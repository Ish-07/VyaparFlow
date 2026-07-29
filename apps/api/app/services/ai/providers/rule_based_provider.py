import time

from app.services.ai.base import REQUIRED_ENTITIES, AIProvider, ParsedCommand
from app.services.nlp_service import parse_command as regex_parse_command


def _build_clarification(intent: str, confidence: float, missing: set[str]) -> str:
    if intent == "UNKNOWN":
        return (
            "I couldn't understand that command. Please clarify what you'd like to do "
            "(sale, expense, or stock update) with the specific details."
        )
    if missing:
        return f"Missing information: {', '.join(sorted(missing))}. Please provide it."
    return (
        f"I parsed this as {intent} but I'm not fully confident "
        f"(confidence {confidence:.2f}). Please confirm the details."
    )


class RuleBasedProvider(AIProvider):
    """Wraps the Step 6 regex parser (app/services/nlp_service.py) so it
    can serve as the fallback path when no real LLM is configured, or
    when the LLM provider is unavailable/times out/returns garbage.
    Deliberately the same limited pattern-matching as before — its job
    here is reliability as a last resort, not sophistication.
    """

    name = "rule_based"

    async def parse_command(self, text: str, business_context: dict) -> ParsedCommand:
        start = time.monotonic()
        parsed = regex_parse_command(text)
        latency_ms = (time.monotonic() - start) * 1000

        required = REQUIRED_ENTITIES.get(parsed.intent, set())
        missing = required - set(parsed.entities.keys())
        requires_confirmation = (
            parsed.intent == "UNKNOWN" or bool(missing) or parsed.confidence < 0.75
        )

        return ParsedCommand(
            intent=parsed.intent,
            confidence=parsed.confidence,
            entities=parsed.entities,
            missing_fields=sorted(missing),
            requires_confirmation=requires_confirmation,
            clarification_question=(
                _build_clarification(parsed.intent, parsed.confidence, missing)
                if requires_confirmation
                else None
            ),
            provider_used=self.name,
            model_used="regex-v1",
            latency_ms=latency_ms,
        )

    async def generate_rag_answer(self, query: str, retrieved_context: list[str]) -> str:
        """No local LLM means no real synthesis — but returning the raw
        matching excerpts is still genuinely useful (the user can read
        them directly) rather than a bare failure. Explicitly labeled as
        unsynthesized so it's never confused with a real generated answer.
        """
        if not retrieved_context:
            return "I don't have enough information in the uploaded documents to answer this."
        excerpts = "\n\n".join(f"- {chunk[:300]}" for chunk in retrieved_context[:3])
        return (
            "AI answer generation is unavailable right now, but here are the most relevant "
            f"excerpts found in your documents:\n\n{excerpts}"
        )
