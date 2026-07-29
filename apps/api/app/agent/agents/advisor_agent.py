"""
Advisor agent: the second agent in a real multi-agent chain.

Per the HLD's Agent Workflow Diagram, a sale should flow
Finance Service -> Analytics Service -> Advisor Agent (restock
suggestion). This node is that last hop - it only runs when
finance_agent sets sale_completed=True (see graph.py's conditional
edge), reads the resulting stock level for the just-sold product, and if
it's now at/below reorder_level, writes a genuine Insight row (the
`insights` table existed since Step 1 but had never been written to
until this step) and appends a restock suggestion to the response the
user actually sees.

This is deliberately a second, independent agent rather than inlined
logic in finance_agent - it's the concrete difference between "one LLM
call dispatching to one handler" and an actual multi-agent handoff.
"""
from uuid import UUID

from app.agent.state import AgentState
from app.agent.tools import tool_create_insight, tool_get_product


def build_advisor_agent(session):
    async def advisor_agent_node(state: AgentState) -> dict:
        business_id = UUID(str(state["business_id"]))
        product_id = state.get("sold_product_id")
        if not product_id:
            return {}

        product = await tool_get_product(session, business_id=business_id, product_id=UUID(product_id))
        if not product or product.stock_quantity > product.reorder_level:
            return {}

        message = (
            f"Restock suggestion: {product.name} is now at {product.stock_quantity} units, "
            f"at or below your reorder level of {product.reorder_level}. Consider restocking soon."
        )
        await tool_create_insight(
            session,
            business_id=business_id,
            insight_type="restock_suggestion",
            message=message,
            confidence=0.9,
        )

        existing_response = state.get("final_response") or ""
        return {
            "final_response": f"{existing_response} {message}".strip(),
            "tool_results": [
                {
                    "agent": "advisor_agent",
                    "tool": "create_insight",
                    "status": "SUCCESS",
                    "insight_type": "restock_suggestion",
                }
            ],
        }

    return advisor_agent_node
