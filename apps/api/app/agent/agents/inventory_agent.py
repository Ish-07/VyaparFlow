"""
Inventory agent: handles STOCK_UPDATE commands.

Resolves the product (by explicit product_id if given, e.g. from a
confirm-flow retry, otherwise by fuzzy name match), then calls the
adjust_stock TOOL — never the repository or session directly. If the
tool raises (product not found, stock policy blocked), this agent
doesn't retry or override anything itself; it routes to clarification
so a human makes the call, per the project's confirmation-required rule
for risky actions.
"""
from uuid import UUID

from fastapi import HTTPException

from app.agent.state import AgentState
from app.agent.tools import tool_adjust_stock, tool_find_product, tool_get_product


def build_inventory_agent(session):
    async def inventory_agent_node(state: AgentState) -> dict:
        business_id = UUID(str(state["business_id"]))
        actor_id = UUID(str(state["user_id"]))

        product = None
        if state.get("product_id"):
            product = await tool_get_product(
                session, business_id=business_id, product_id=UUID(str(state["product_id"]))
            )
        elif state.get("product_name"):
            product = await tool_find_product(
                session, business_id=business_id, product_name=state["product_name"]
            )

        if not product:
            return {
                "status": "NEEDS_CONFIRMATION",
                "final_response": (
                    f"I couldn't find a product matching '{state.get('product_name')}'. "
                    "Please confirm the correct product_id via /voice-commands/{id}/confirm."
                ),
            }

        try:
            result = await tool_adjust_stock(
                session,
                business_id=business_id,
                actor_id=actor_id,
                product_id=product.id,
                quantity_change=state["quantity"],
                confirm_negative_stock=state.get("confirm_negative_stock", False),
            )
        except HTTPException as exc:
            return {
                "status": "NEEDS_CONFIRMATION",
                "final_response": (
                    f"Could not update stock: {exc.detail}. Resubmit via /confirm with "
                    "confirm_negative_stock=true to override, or correct the details."
                ),
                "tool_results": [
                    {"agent": "inventory_agent", "tool": "adjust_stock", "status": "FAILED", "error": str(exc.detail)}
                ],
            }

        return {
            "status": "COMPLETED",
            "final_response": f"Stock updated: {product.name} now at {result.product.stock_quantity}.",
            "tool_results": [
                {
                    "agent": "inventory_agent",
                    "tool": "adjust_stock",
                    "status": "SUCCESS",
                    "product_id": str(product.id),
                    "new_stock_quantity": float(result.product.stock_quantity),
                }
            ],
        }

    return inventory_agent_node
