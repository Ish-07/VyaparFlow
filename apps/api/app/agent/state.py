"""
Shared state for the VyaparFlow agent graph.

This mirrors the "Graph State" design from the project's own Agentic AI
transcript (command_id, business_id, transcript, intent, entities,
confidence, tool_results, final_response, requires_confirmation) — the
same fields that used to live as ad-hoc local variables inside
VoiceCommandService._route() now live here as explicit, typed graph
state, since a real LangGraph StateGraph (not an if/elif chain) is what
actually earns calling this a multi-agent system.
"""
import operator
from typing import Annotated, Any, TypedDict
from uuid import UUID


class AgentState(TypedDict, total=False):
    # ---- Identity / tenant context (read-only for every node) ----
    command_id: UUID
    business_id: UUID
    user_id: UUID

    # ---- Understanding (filled in before the graph runs, by AIRouter) ----
    transcript: str
    intent: str
    confidence: float
    entities_raw: dict  # the ParsedCommand's original entities dict, before flattening
    _confidence_threshold: float  # from settings, passed in so supervisor doesn't need config directly

    # ---- Entities, flattened for direct node use. The supervisor merges
    # parsed entities into these; the confirm-flow can override any of
    # them with explicit values (e.g. an exact product_id after a
    # "product not found" clarification). ----
    product_name: str | None
    product_id: str | None  # str, not UUID: keeps the state JSON/checkpoint-serializable
    quantity: float | None
    unit_price: float | None
    amount: float | None
    category: str | None
    payment_status: str
    customer_id: str | None
    confirm_negative_stock: bool

    # ---- Routing decision made by the supervisor node ----
    next_agent: str  # "inventory_agent" | "finance_agent" | "clarification_agent"

    # Results, filled in by whichever agent actually executes. Annotated
    # with operator.add so each node's tool_results APPENDS to the list
    # rather than overwriting it — without this, LangGraph's default
    # merge behavior means a later node (e.g. advisor_agent) silently
    # clobbers an earlier node's results (e.g. finance_agent's
    # record_sale) instead of both being preserved in the trace.
    status: str  # COMPLETED | NEEDS_CONFIRMATION | FAILED
    final_response: str | None
    tool_results: Annotated[list[dict[str, Any]], operator.add]

    # ---- Advisor chaining: only meaningful after a successful SALE ----
    sale_completed: bool
    sold_product_id: str | None
