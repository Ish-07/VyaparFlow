import json
import logging
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

logger = logging.getLogger("vyaparflow.ai.nvidia_nim")

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


_RAG_SYSTEM_PROMPT = """You are answering a small business owner's question using ONLY the \
provided context excerpts from their own uploaded business documents. Follow these rules strictly:

- Answer ONLY from the provided context. Do not use outside knowledge or invent facts, prices, \
dates, policies, or numbers not present in the context.
- If the context does not contain enough information to answer, say clearly that you don't have \
enough information in the uploaded documents to answer this, rather than guessing.
- Keep the answer short and conversational, suitable for reading aloud or as a text reply — a \
few sentences, not an essay.
- Do not mention "the context" or "the excerpts" explicitly; answer naturally as if you simply \
know this about their business.
"""


class NvidiaNimProvider(AIProvider):
    """NVIDIA NIM's inference endpoints are OpenAI-compatible, so this
    reuses the standard `openai` SDK pointed at NVIDIA's base_url instead
    of a NIM-specific client — see the abstraction's whole point: minimal
    provider-specific code.
    """

    name = "nvidia_nim"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        embedding_model: str = "nvidia/nemotron-3-embed-1b",
    ):
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url, timeout=timeout_seconds)
        self._model = model
        self._embedding_model = embedding_model

    async def parse_command(self, text: str, business_context: dict) -> ParsedCommand:
        known_products = business_context.get("known_products") or []
        user_content = text
        if known_products:
            user_content += f"\n\nKnown product names for this business: {', '.join(known_products)}"

        start = time.monotonic()
        logger.info("Calling NVIDIA NIM model=%s for command: %r", self._model, text[:120])
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
        logger.info("NVIDIA NIM responded in %.0fms: %r", latency_ms, raw[:300])
        parsed = self._parse_json_response(raw)

        intent = parsed.get("intent", "UNKNOWN")
        entities = parsed.get("entities") or {}
        confidence = float(parsed.get("confidence", 0.0))
        logger.info(
            "Parsed as intent=%s confidence=%.2f entities=%s", intent, confidence, entities
        )

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

    async def create_embedding(self, text: str, *, input_type: str = "passage") -> list[float]:
        if input_type not in ("passage", "query"):
            raise ValueError(f"input_type must be 'passage' or 'query', got {input_type!r}")

        start = time.monotonic()
        try:
            response = await self._client.embeddings.create(
                model=self._embedding_model,
                input=[text],
                encoding_format="float",
                extra_body={"input_type": input_type, "truncate": "END"},
            )
        except RateLimitError as exc:
            raise AIProviderRateLimitError(str(exc)) from exc
        except APITimeoutError as exc:
            raise AIProviderTimeoutError(str(exc)) from exc
        except (APIConnectionError, APIStatusError) as exc:
            raise AIProviderTimeoutError(str(exc)) from exc

        latency_ms = (time.monotonic() - start) * 1000
        vector = response.data[0].embedding
        logger.info(
            "NVIDIA NIM embedding (%s mode) in %.0fms, dim=%d", input_type, latency_ms, len(vector)
        )
        return vector

    async def generate_rag_answer(self, query: str, retrieved_context: list[str]) -> str:
        if not retrieved_context:
            return "I don't have enough information in the uploaded documents to answer this."

        context_block = "\n\n---\n\n".join(
            f"Excerpt {i + 1}:\n{chunk}" for i, chunk in enumerate(retrieved_context)
        )
        try:
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": _RAG_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"Context:\n{context_block}\n\nQuestion: {query}",
                    },
                ],
                temperature=0.2,
                max_tokens=400,
                stream=False,
            )
        except RateLimitError as exc:
            raise AIProviderRateLimitError(str(exc)) from exc
        except APITimeoutError as exc:
            raise AIProviderTimeoutError(str(exc)) from exc
        except (APIConnectionError, APIStatusError) as exc:
            raise AIProviderTimeoutError(str(exc)) from exc

        return (completion.choices[0].message.content or "").strip()

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
