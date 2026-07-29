"""
Finance agent: handles SALE and EXPENSE commands.

For a SALE, sets sale_completed=True and sold_product_id on success -
this is what the graph's conditional edge reads to decide whether to
chain into advisor_agent next. This is the actual multi-agent handoff in
this build: Finance -> Advisor, matching the HLD's Agent Workflow Diagram
("Finance Service -> Analytics Service -> Advisor Agent") rather than a
single agent handling one command in isolation.
"""
from uuid import UUID

from fastapi import HTTPException

from app.agent.state import AgentState
from app.agent.tools import tool_find_product, tool_get_product, tool_record_expense, tool_record_sale


def build_finance_agent(session):
    async def finance_agent_node(state: AgentState) -> dict:
        business_id = UUID(str(state["business_id"]))
        actor_id = UUID(str(state["user_id"]))
        intent = state["intent"]

        if intent == "EXPENSE":
            expense = await tool_record_expense(
                session,
                business_id=business_id,
                actor_id=actor_id,
                amount=state["amount"],
                category=state["category"],
            )
            return {
                "status": "COMPLETED",
                "final_response": f"Expense recorded: {state['amount']} for {state['category']}.",
                "tool_results": [
                    {"agent": "finance_agent", "tool": "record_expense", "status": "SUCCESS", "expense_id": str(expense.id)}
                ],
            }

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
            customer_id = UUID(state["customer_id"]) if state.get("customer_id") else None
            txn = await tool_record_sale(
                session,
                business_id=business_id,
                actor_id=actor_id,
                product_id=product.id,
                quantity=state["quantity"],
                unit_price=state["unit_price"],
                payment_status=state.get("payment_status") or "PAID",
                customer_id=customer_id,
                confirm_negative_stock=state.get("confirm_negative_stock", False),
            )
        except HTTPException as exc:
            return {
                "status": "NEEDS_CONFIRMATION",
                "final_response": (
                    f"Could not complete the sale: {exc.detail}. Resubmit via /confirm with "
                    "confirm_negative_stock=true to override, or correct the details."
                ),
                "tool_results": [
                    {"agent": "finance_agent", "tool": "record_sale", "status": "FAILED", "error": str(exc.detail)}
                ],
            }

        return {
            "status": "COMPLETED",
            "final_response": f"Sale recorded: {state['quantity']} {product.name} for {txn.amount} total.",
            "sale_completed": True,
            "sold_product_id": str(product.id),
            "tool_results": [
                {
                    "agent": "finance_agent",
                    "tool": "record_sale",
                    "status": "SUCCESS",
                    "transaction_id": str(txn.id),
                    "amount": float(txn.amount),
                }
            ],
        }

    return finance_agent_node
