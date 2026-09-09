import json
import logging
import time

import httpx
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
    AIProviderError,
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    ParsedCommand,
)

logger = logging.getLogger("vyaparflow.ai.gemini")


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
- confidence is your honest estimate from 0.0 to 1.0 of how certain you are about BOTH the
  intent and every entity value.
- If the command is ambiguous or missing key details, use a low confidence.
- If details are missing, set clarification_question to a short, specific question.
- Otherwise set clarification_question to null.
- Never invent a product name, price, or quantity.
"""


_RAG_SYSTEM_PROMPT = """You are answering a small business owner's question using ONLY the \
provided context excerpts from their own uploaded business documents.

Rules:
- Answer ONLY from the provided context.
- Do not use outside knowledge or invent facts, prices, dates, policies, or numbers.
- If the context is insufficient, clearly say that the uploaded documents do not contain enough
  information to answer.
- Keep the answer short and conversational.
- Do not mention "the context" or "the excerpts" explicitly.
"""


class GeminiProvider(AIProvider):
    """Google Gemini provider.

    Chat requests use Gemini's OpenAI-compatible endpoint.
    Embeddings use Gemini's native embedContent endpoint because the
    NVIDIA-specific embedding fields are not supported by Gemini.
    """

    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: float,
        rag_model: str | None = None,
        embedding_model: str = "gemini-embedding-001",
        embedding_dimension: int = 1536,
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._embedding_dimension = embedding_dimension

        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )

        self._model = model
        self._rag_model = rag_model or model
        self._embedding_model = embedding_model
        self.embedding_model = embedding_model

    async def parse_command(
        self,
        user_content: str,
        business_context: dict | None = None,
    ) -> ParsedCommand:
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
        except APIConnectionError as exc:
            raise AIProviderTimeoutError(str(exc)) from exc
        except APIStatusError as exc:
            if exc.status_code == 429:
                raise AIProviderRateLimitError(str(exc)) from exc
            raise AIProviderError(
                f"Gemini chat request failed with HTTP {exc.status_code}: {exc}"
            ) from exc

        latency_ms = (time.monotonic() - start) * 1000
        raw = completion.choices[0].message.content or ""

        logger.info(
            "Gemini command response in %.0fms: %r",
            latency_ms,
            raw[:300],
        )

        parsed = self._parse_json_response(raw)

        intent = str(parsed.get("intent", "UNKNOWN"))
        entities = parsed.get("entities") or {}
        confidence = float(parsed.get("confidence", 0.0))

        required = REQUIRED_ENTITIES.get(intent, set())
        missing = sorted(required - set(entities.keys()))

        requires_confirmation = (
            bool(missing)
            or intent == "UNKNOWN"
            or confidence < 0.75
        )

        clarification = parsed.get("clarification_question")

        if requires_confirmation and not clarification:
            if missing:
                clarification = (
                    f"Missing information: {', '.join(missing)}. "
                    "Please provide it."
                )
            elif intent == "UNKNOWN":
                clarification = "I couldn't understand that command. Please clarify."
            else:
                clarification = (
                    f"I parsed this as {intent}, but I'm not fully confident. "
                    "Please confirm the details."
                )

        return ParsedCommand(
            intent=intent,
            confidence=confidence,
            entities=entities,
            missing_fields=missing,
            requires_confirmation=requires_confirmation,
            clarification_question=(
                clarification if requires_confirmation else None
            ),
            provider_used=self.name,
            model_used=self._model,
            latency_ms=latency_ms,
        )

    async def create_embedding(
        self,
        text: str,
        *,
        input_type: str = "passage",
    ) -> list[float]:
        if input_type not in ("passage", "query"):
            raise ValueError(
                f"input_type must be 'passage' or 'query', got {input_type!r}"
            )

        task_type = (
            "RETRIEVAL_DOCUMENT"
            if input_type == "passage"
            else "RETRIEVAL_QUERY"
        )

        model_name = self._embedding_model.removeprefix("models/")

        payload = {
            "model": f"models/{model_name}",
            "content": {
                "parts": [
                    {
                        "text": text,
                    }
                ]
            },
            "taskType": task_type,
            "outputDimensionality": self._embedding_dimension,
        }

        url = (
            "https://generativelanguage.googleapis.com/v1beta/"
            f"models/{model_name}:embedContent"
        )

        start = time.monotonic()

        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds
            ) as client:
                response = await client.post(
                    url,
                    headers={
                        "x-goog-api-key": self._api_key,
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise AIProviderTimeoutError(str(exc)) from exc
        except httpx.RequestError as exc:
            raise AIProviderTimeoutError(str(exc)) from exc

        if response.status_code == 429:
            raise AIProviderRateLimitError(
                f"Gemini embedding rate limit: {response.text[:300]}"
            )

        if response.status_code >= 400:
            raise AIProviderError(
                "Gemini embedding request failed with "
                f"HTTP {response.status_code}: {response.text[:300]}"
            )

        try:
            vector = response.json()["embedding"]["values"]
        except (KeyError, TypeError, ValueError) as exc:
            raise AIProviderInvalidResponseError(
                f"Gemini returned an invalid embedding response: "
                f"{response.text[:300]}"
            ) from exc

        vector = [float(value) for value in vector]

        if len(vector) != self._embedding_dimension:
            raise AIProviderInvalidResponseError(
                "Gemini returned an unexpected embedding dimension: "
                f"expected {self._embedding_dimension}, got {len(vector)}"
            )

        latency_ms = (time.monotonic() - start) * 1000

        logger.info(
            "Gemini embedding (%s mode) in %.0fms, dim=%d",
            input_type,
            latency_ms,
            len(vector),
        )

        return vector

    async def generate_rag_answer(
        self,
        query: str,
        retrieved_context: list[str],
    ) -> str:
        if not retrieved_context:
            return (
                "I don't have enough information in the uploaded "
                "documents to answer this."
            )

        context_block = "\n\n---\n\n".join(
            f"Excerpt {index + 1}:\n{chunk}"
            for index, chunk in enumerate(retrieved_context)
        )

        try:
            completion = await self._client.chat.completions.create(
                model=self._rag_model,
                messages=[
                    {
                        "role": "system",
                        "content": _RAG_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Context:\n{context_block}\n\n"
                            f"Question: {query}"
                        ),
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
        except APIConnectionError as exc:
            raise AIProviderTimeoutError(str(exc)) from exc
        except APIStatusError as exc:
            if exc.status_code == 429:
                raise AIProviderRateLimitError(str(exc)) from exc
            raise AIProviderError(
                f"Gemini RAG request failed with HTTP {exc.status_code}: {exc}"
            ) from exc

        return (completion.choices[0].message.content or "").strip()

    @staticmethod
    def _parse_json_response(raw: str) -> dict:
        text = raw.strip()

        if text.startswith("```"):
            text = text.strip("`").strip()

            if text.lower().startswith("json"):
                text = text[4:].strip()

        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AIProviderInvalidResponseError(
                f"Non-JSON response: {raw[:200]!r}"
            ) from exc

        if not isinstance(data, dict) or "intent" not in data:
            raise AIProviderInvalidResponseError(
                f"JSON missing required 'intent' field: {data!r}"
            )

        return data