import logging

from app.core.config import get_settings
from app.services.ai.base import AIProvider, AIProviderError, ParsedCommand
from app.services.ai.providers.nvidia_nim_provider import NvidiaNimProvider
from app.services.ai.providers.rule_based_provider import RuleBasedProvider

logger = logging.getLogger("vyaparflow.ai_router")

settings = get_settings()


def _build_primary_provider() -> AIProvider | None:
    """Returns None if no LLM_API_KEY is configured — lets local/dev
    setups run on the rule-based fallback with zero AI config, per the
    spec's dev-mode requirement, without crashing on a missing key.
    """
    if settings.llm_provider == "nvidia_nim" and settings.llm_api_key:
        return NvidiaNimProvider(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_command_model,
            timeout_seconds=settings.ai_request_timeout_seconds,
        )
    return None


class AIRouter:
    """The single entry point business logic should call for anything
    AI-related. Handles primary -> retry -> fallback so callers (e.g.
    VoiceCommandService) never deal with provider-specific failure modes.
    """

    def __init__(self, primary: AIProvider | None = None, fallback: AIProvider | None = None):
        self._primary = primary if primary is not None else _build_primary_provider()
        self._fallback = fallback if fallback is not None else RuleBasedProvider()

    async def parse_command(self, text: str, business_context: dict | None = None) -> ParsedCommand:
        business_context = business_context or {}

        if self._primary is None:
            result = await self._fallback.parse_command(text, business_context)
            result.fallback_reason = "no_llm_configured"
            return result

        last_error: Exception | None = None
        attempts = 1 + max(settings.ai_max_retries, 0)
        for attempt in range(attempts):
            try:
                return await self._primary.parse_command(text, business_context)
            except AIProviderError as exc:
                last_error = exc
                logger.warning(
                    "AI provider %s failed (attempt %d/%d): %s",
                    self._primary.name,
                    attempt + 1,
                    attempts,
                    exc,
                )

        if settings.enable_rule_based_ai_fallback:
            result = await self._fallback.parse_command(text, business_context)
            result.fallback_reason = f"primary_failed:{type(last_error).__name__}"
            return result

        return ParsedCommand(
            intent="UNKNOWN",
            confidence=0.0,
            requires_confirmation=True,
            clarification_question=(
                "The AI service is temporarily unavailable and rule-based fallback is "
                "disabled. Please try again shortly or contact support."
            ),
            provider_used="none",
            model_used="none",
            fallback_reason=f"primary_failed_no_fallback:{type(last_error).__name__}",
        )
