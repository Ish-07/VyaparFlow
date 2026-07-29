"""
Supervisor node: the graph's entry point and routing brain.

Per the project's HLD ("The Supervisor Agent is the orchestration brain.
It creates a workflow plan and calls domain services through controlled
tools"), this node owns ONE decision: which specialized agent should act
next. It does not itself touch the database or call any tool — it only
reads the already-parsed intent/entities (from AIRouter, upstream of the
graph) and decides where to route.

Safety note: this node does NOT get to decide "this is safe, skip
validation" — it can send a command to clarification_agent, but every
path that reaches inventory_agent/finance_agent still goes through full
service-layer validation (stock policy, tenant scope, confirmation
rules). See VoiceCommandService docstring for the fuller safety chain.
"""
from app.agent.state import AgentState
from app.services.ai.base import REQUIRED_ENTITIES


async def supervisor_node(state: AgentState) -> dict:
    intent = state.get("intent", "UNKNOWN")
    confidence = state.get("confidence", 0.0)
    entities = state.get("entities_raw", {}) or {}

    updates: dict = {
        "product_name": state.get("product_name") or entities.get("product_name"),
        "quantity": state.get("quantity") or entities.get("quantity"),
        "unit_price": state.get("unit_price") or entities.get("unit_price"),
        "amount": state.get("amount") or entities.get("amount"),
        "category": state.get("category") or entities.get("category"),
    }

    required = REQUIRED_ENTITIES.get(intent)
    confidence_threshold = state.get("_confidence_threshold", 0.75)

    if intent == "UNKNOWN" or required is None:
        updates["next_agent"] = "clarification_agent"
        updates["final_response"] = (
            "I couldn't understand that command. Please clarify what you'd like to do "
            "(sale, expense, or stock update) with the specific details."
        )
        return updates

    if confidence < confidence_threshold:
        updates["next_agent"] = "clarification_agent"
        updates["final_response"] = (
            f"I parsed this as {intent} but I'm not fully confident "
            f"(confidence {confidence:.2f}). Please confirm the details."
        )
        return updates

    merged = {**entities, **{k: v for k, v in updates.items() if v is not None}}
    missing = required - {k for k, v in merged.items() if v is not None}
    if missing:
        updates["next_agent"] = "clarification_agent"
        updates["final_response"] = f"Missing information: {', '.join(sorted(missing))}. Please provide it."
        return updates

    if intent in ("SALE", "EXPENSE"):
        updates["next_agent"] = "finance_agent"
    elif intent == "STOCK_UPDATE":
        updates["next_agent"] = "inventory_agent"
    elif intent == "QUERY":
        updates["next_agent"] = "rag_agent"
    else:
        updates["next_agent"] = "clarification_agent"
        updates["final_response"] = f"No agent is wired up yet for intent {intent}."

    return updates
