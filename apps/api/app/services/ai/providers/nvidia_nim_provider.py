import json
import time

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    RateLimitError,
)

from app.services.ai.base import (
    REQUIRED_ENTITIES,
    AIProvider,
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    ParsedCommand,
)

_SYSTEM_PROMPT = """You are the command-understanding layer for VyaparFlow, a small-business \
management system. Given a short business command (possibly in English, Hindi, or Hinglish), \
extract the intent and structured entities.

Valid intents: SALE, EXPENSE, STOCK_UPDATE, CUSTOMER_UPDATE, QUERY, UNKNOWN.

Entity fields by intent:
- SALE: product_name (string), quantity (number), unit_price (number, per-unit price)
- EXPENSE: amount (number), category (string)
- STOCK_UPDATE: product_name (string), quantity (number, positive to add/restock)
- CUSTOMER_UPDATE / QUERY: whatever relevant fields you can extract; these are not yet executed.

Respond with STRICT JSON ONLY, no prose, no markdown fences, matching exactly this shape:
{
  "intent": "SALE | EXPENSE | STOCK_UPDATE | CUSTOMER_UPDATE | QUERY | UNKNOWN",
  "confidence": 0.0,
  "entities": {},
  "clarification_question": null
}

Rules:
- confidence is your own honest estimate (0.0-1.0) of how certain you are about BOTH the \
intent and every entity value. If the command is ambiguous, vague, or missing key details, \
use a low confidence rather than guessing.
- If you are not confident, or details are genuinely missing, set clarification_question to a \
short, specific question asking the user for exactly what's missing. Otherwise set it to null.
- Never invent a product name, price, or quantity that isn't stated or strongly implied by the text.
- If a list of known product names is provided below, prefer matching product_name to one of \
them (case-insensitive) when the text clearly refers to it, but still return what the text says \
if nothing matches.
"""


class NvidiaNimProvider(AIProvider):
    """NVIDIA NIM's inference endpoints are OpenAI-compatible, so this
    reuses the standard `openai` SDK pointed at NVIDIA's base_url instead
    of a NIM-specific client — see the abstraction's whole point: minimal
    provider-specific code.
    """

    name = "nvidia_nim"

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_seconds: float):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
        self._model = model

    async def parse_command(self, text: str, business_context: dict) -> ParsedCommand:
        known_products = business_context.get("known_products") or []
        user_content = text
        if known_products:
            user_content += f"\n\nKnown product names for this business: {', '.join(known_products)}"

        start = time.monotonic()
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                top_p=0.7,
                max_tokens=500,
                stream=False,
            )
        except RateLimitError as exc:
            raise AIProviderRateLimitError(str(exc)) from exc
        except APITimeoutError as exc:
            raise AIProviderTimeoutError(str(exc)) from exc
        except (APIConnectionError, APIStatusError) as exc:
            # Connection issues and 5xx/4xx errors are both treated as
            # "this provider isn't working right now" — the router falls
            # back the same way regardless of the exact cause.
            raise AIProviderTimeoutError(str(exc)) from exc

        latency_ms = (time.monotonic() - start) * 1000
        raw = completion.choices[0].message.content or ""
        parsed = self._parse_json_response(raw)

        intent = parsed.get("intent", "UNKNOWN")
        entities = parsed.get("entities") or {}
        confidence = float(parsed.get("confidence", 0.0))

        # Belt-and-suspenders: never trust the LLM's own judgment of
        # "nothing's missing" — recompute against our own required-field
        # table. This is the concrete enforcement of "final business
        # validation stays in FastAPI services, not the LLM."
        required = REQUIRED_ENTITIES.get(intent, set())
        missing = sorted(required - set(entities.keys()))
        requires_confirmation = bool(missing) or intent == "UNKNOWN" or confidence < 0.75

        clarification = parsed.get("clarification_question")
        if requires_confirmation and not clarification:
            if missing:
                clarification = f"Missing information: {', '.join(missing)}. Please provide it."
            elif intent == "UNKNOWN":
                clarification = "I couldn't understand that command. Please clarify."
            else:
                clarification = (
                    f"I parsed this as {intent} but I'm not fully confident "
                    f"(confidence {confidence:.2f}). Please confirm the details."
                )

        return ParsedCommand(
            intent=intent,
            confidence=confidence,
            entities=entities,
            missing_fields=missing,
            requires_confirmation=requires_confirmation,
            clarification_question=clarification if requires_confirmation else None,
            provider_used=self.name,
            model_used=self._model,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        text = raw.strip()
        # Models sometimes wrap JSON in markdown fences despite instructions
        # not to — strip that defensively rather than failing outright.
        if text.startswith("```"):
            text = text.strip("`")
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIProviderInvalidResponseError(f"Non-JSON response: {raw[:200]!r}") from exc
        if not isinstance(data, dict) or "intent" not in data:
            raise AIProviderInvalidResponseError(f"JSON missing required 'intent' field: {data!r}")
        return data
