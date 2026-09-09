"""
Tests for the AI provider abstraction (app/services/ai/).

These use a MOCKED OpenAI client — no real network call to Gemini is
made. This is deliberate: it lets the test suite run in CI/any machine
without an API key, while still verifying the actual logic (JSON parsing,
markdown-fence stripping, error-type mapping, retry-then-fallback
behavior) rather than just trusting the code reads correctly.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from openai import APIConnectionError, APITimeoutError, RateLimitError

from app.services.ai.base import (
    AIProviderInvalidResponseError,
    AIProviderRateLimitError,
    AIProviderTimeoutError,
    ParsedCommand,
)
from app.services.ai.providers.gemini_provider import GeminiProvider
from app.services.ai.providers.rule_based_provider import RuleBasedProvider
from app.services.ai.router import AIRouter, settings


def _make_completion(content: str):
    """Builds a fake object shaped like openai's ChatCompletion response,
    just deep enough for GeminiProvider to read .choices[0].message.content
    """
    message = MagicMock()
    message.content = content
    choice = MagicMock()
    choice.message = message
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def _provider_with_mocked_client(response_content: str | None = None, side_effect=None):
    provider = GeminiProvider(
        api_key="fake-key", base_url="https://fake.example/v1", model="fake-model", timeout_seconds=5.0
    )
    provider._client = MagicMock()
    provider._client.chat = MagicMock()
    provider._client.chat.completions = MagicMock()
    if side_effect is not None:
        provider._client.chat.completions.create = AsyncMock(side_effect=side_effect)
    else:
        provider._client.chat.completions.create = AsyncMock(
            return_value=_make_completion(response_content)
        )
    return provider


class TestGeminiProviderParsing:
    async def test_valid_json_sale_parsed_correctly(self):
        provider = _provider_with_mocked_client(
            json.dumps(
                {
                    "intent": "SALE",
                    "confidence": 0.95,
                    "entities": {"product_name": "pickle bottle", "quantity": 5, "unit_price": 100},
                    "clarification_question": None,
                }
            )
        )
        result = await provider.parse_command("sold 5 pickle bottles for 100 each", {})
        assert result.intent == "SALE"
        assert result.confidence == 0.95
        assert result.entities["quantity"] == 5
        assert result.requires_confirmation is False
        assert result.provider_used == "gemini"

    async def test_markdown_fenced_json_is_stripped(self):
        fenced = '```json\n{"intent": "EXPENSE", "confidence": 0.9, "entities": {"amount": 500, "category": "rent"}}\n```'
        provider = _provider_with_mocked_client(fenced)
        result = await provider.parse_command("spent 500 on rent", {})
        assert result.intent == "EXPENSE"
        assert result.entities["category"] == "rent"

    async def test_missing_required_entity_forces_confirmation(self):
        """Even if the LLM claims high confidence, missing a REQUIRED
        entity must still force requires_confirmation=True — this is the
        'never trust the LLM's self-report blindly' safety behavior."""
        provider = _provider_with_mocked_client(
            json.dumps(
                {
                    "intent": "SALE",
                    "confidence": 0.99,
                    "entities": {"product_name": "pickle bottle", "quantity": 5},  # unit_price missing
                }
            )
        )
        result = await provider.parse_command("sold 5 pickle bottles", {})
        assert result.requires_confirmation is True
        assert "unit_price" in result.missing_fields

    async def test_non_json_response_raises_invalid_response_error(self):
        provider = _provider_with_mocked_client("Sure, here's a sale for you: ...")
        with pytest.raises(AIProviderInvalidResponseError):
            await provider.parse_command("sold something", {})

    async def test_json_missing_intent_field_raises(self):
        provider = _provider_with_mocked_client(json.dumps({"confidence": 0.9, "entities": {}}))
        with pytest.raises(AIProviderInvalidResponseError):
            await provider.parse_command("garbled", {})

    async def test_rate_limit_error_mapped(self):
        provider = _provider_with_mocked_client(
            side_effect=RateLimitError("rate limited", response=MagicMock(status_code=429), body=None)
        )
        with pytest.raises(AIProviderRateLimitError):
            await provider.parse_command("anything", {})

    async def test_timeout_error_mapped(self):
        provider = _provider_with_mocked_client(side_effect=APITimeoutError(request=MagicMock()))
        with pytest.raises(AIProviderTimeoutError):
            await provider.parse_command("anything", {})

    async def test_connection_error_mapped_to_timeout_family(self):
        provider = _provider_with_mocked_client(
            side_effect=APIConnectionError(request=MagicMock())
        )
        with pytest.raises(AIProviderTimeoutError):
            await provider.parse_command("anything", {})


class TestRuleBasedProvider:
    async def test_wraps_regex_parser_sale(self):
        provider = RuleBasedProvider()
        result = await provider.parse_command("sold 5 pickle bottles for 100 rupees each", {})
        assert result.intent == "SALE"
        assert result.provider_used == "rule_based"
        assert result.requires_confirmation is False  # confidence 0.9 >= 0.75, all entities present

    async def test_unknown_text_requires_confirmation(self):
        provider = RuleBasedProvider()
        result = await provider.parse_command("blah blah nonsense", {})
        assert result.intent == "UNKNOWN"
        assert result.requires_confirmation is True
        assert result.clarification_question is not None


class TestAIRouterFallback:
    async def test_no_api_key_goes_straight_to_fallback(self, monkeypatch):
        monkeypatch.setattr(settings, "llm_api_key", None)

        router = AIRouter(primary=None, fallback=RuleBasedProvider())

        result = await router.parse_command(
            "sold 5 pickle bottles for 100 rupees each"
        )

        assert result.provider_used == "rule_based"
        assert result.fallback_reason == "no_llm_configured"

    async def test_primary_success_does_not_touch_fallback(self):
        primary = _provider_with_mocked_client(
            json.dumps({"intent": "SALE", "confidence": 0.9, "entities": {
                "product_name": "x", "quantity": 1, "unit_price": 1
            }})
        )
        fallback = RuleBasedProvider()
        fallback.parse_command = AsyncMock(side_effect=AssertionError("fallback should not be called"))
        router = AIRouter(primary=primary, fallback=fallback)
        result = await router.parse_command("sold 1 x for 1 each")
        assert result.provider_used == "gemini"

    async def test_primary_failure_falls_back_with_reason(self):
        primary = _provider_with_mocked_client(
            side_effect=APITimeoutError(request=MagicMock())
        )
        router = AIRouter(primary=primary, fallback=RuleBasedProvider())
        result = await router.parse_command("sold 5 pickle bottles for 100 rupees each")
        assert result.provider_used == "rule_based"
        assert result.fallback_reason.startswith("primary_failed:")

    async def test_retries_before_falling_back(self, monkeypatch):
        monkeypatch.setattr(settings, "ai_max_retries", 1)

        primary = _provider_with_mocked_client(
            side_effect=APITimeoutError(request=MagicMock())
        )
        router = AIRouter(primary=primary, fallback=RuleBasedProvider())

        await router.parse_command("anything")

        assert primary._client.chat.completions.create.call_count == 2
