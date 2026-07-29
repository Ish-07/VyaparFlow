"""
Provider-agnostic AI abstraction.

Every provider (NVIDIA NIM, rule-based fallback, and later Gemini/others)
implements this same interface. Business logic (VoiceCommandService, and
later the RAG/agent layers) only ever talks to AIRouter — never to a
provider class directly — so switching or adding providers is a config
change, not a rewrite.

SAFETY NOTE, non-negotiable across every provider implementation: the AI
layer's job ends at producing a ParsedCommand. It never touches the
database, never calls a service that mutates state, and its output is
always re-validated by FastAPI services (tenant scope, product existence,
stock policy, confirmation rules) before anything executes. An LLM
hallucinating "confidence: 1.0, requires_confirmation: false" cannot skip
those checks — see VoiceCommandService._route, which recomputes
missing/required entities itself rather than trusting the provider's
self-reported flags blindly.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    SALE = "SALE"
    EXPENSE = "EXPENSE"
    STOCK_UPDATE = "STOCK_UPDATE"
    CUSTOMER_UPDATE = "CUSTOMER_UPDATE"
    QUERY = "QUERY"
    UNKNOWN = "UNKNOWN"


# Required entity keys per intent — used by every provider (LLM or
# rule-based) to compute `missing_fields`, and re-checked independently by
# VoiceCommandService regardless of what a provider reports.
REQUIRED_ENTITIES: dict[str, set[str]] = {
    "SALE": {"product_name", "quantity", "unit_price"},
    "EXPENSE": {"amount", "category"},
    "STOCK_UPDATE": {"product_name", "quantity"},
}


@dataclass
class ParsedCommand:
    intent: str
    confidence: float
    entities: dict = field(default_factory=dict)
    missing_fields: list[str] = field(default_factory=list)
    requires_confirmation: bool = False
    clarification_question: str | None = None

    # Observability metadata (not part of the LLM's own JSON output —
    # filled in by the router/provider after the call completes).
    provider_used: str = "unknown"
    model_used: str = "unknown"
    latency_ms: float = 0.0
    fallback_reason: str | None = None


class AIProviderError(Exception):
    """Base class for recoverable provider failures the router should
    catch and act on (retry, or fall back to the next provider)."""


class AIProviderTimeoutError(AIProviderError):
    pass


class AIProviderRateLimitError(AIProviderError):
    pass


class AIProviderInvalidResponseError(AIProviderError):
    """Raised when the provider responded, but not with parseable/valid
    JSON matching the expected schema."""


class AIProvider(ABC):
    """Interface every provider implements. RAG/translation/agent-
    supervision methods are declared now (per the spec's 'agentic
    foundation' requirement) but raise NotImplementedError until their
    own build steps (RAG pipeline, LangGraph supervisor, voice pipeline).
    Only parse_command is live in this step.
    """

    name: str = "base"

    @abstractmethod
    async def parse_command(self, text: str, business_context: dict) -> ParsedCommand:
        ...

    async def supervise_agent(self, state: dict) -> dict:
        raise NotImplementedError("Agent supervision arrives with the LangGraph step.")

    async def generate_rag_answer(self, query: str, retrieved_context: list[str]) -> str:
        raise NotImplementedError("RAG answer generation arrives with the RAG pipeline step.")

    async def create_embedding(self, text: str) -> list[float]:
        raise NotImplementedError("Embeddings arrive with the RAG pipeline step.")

    async def translate_text(self, text: str, source_language: str, target_language: str) -> str:
        raise NotImplementedError("Translation arrives with the voice pipeline step.")
