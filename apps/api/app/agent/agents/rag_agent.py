"""
RAG agent: handles QUERY commands — questions about the business's own
uploaded documents ("what does my supplier invoice say about payment
terms").

Unlike finance_agent/inventory_agent, this agent never mutates any
business-state row (no stock/transaction/customer changes) — it only
reads, embeds, retrieves, and generates a grounded answer via
RAGService, then reports that answer back as the command's final
response. Kept as its own tool call (not inlined into the supervisor)
for the same reason every other agent is separate: consistency, and so
a future step (multi-hop RAG, e.g. "check the invoice AND remind me to
pay it") has a clean second agent to chain into, the same way advisor_agent
chains off finance_agent today.
"""
from uuid import UUID

from app.agent.state import AgentState
from app.services.rag_service import RAGService


def build_rag_agent(session):
    async def rag_agent_node(state: AgentState) -> dict:
        business_id = UUID(str(state["business_id"]))
        query = state.get("transcript", "")

        result = await RAGService(session).answer_question(business_id=business_id, query=query)

        return {
            "status": "COMPLETED",
            "final_response": result.answer,
            "tool_results": [
                {
                    "agent": "rag_agent",
                    "tool": "answer_question",
                    "status": "SUCCESS",
                    "provider_used": result.provider_used,
                    "source_count": len(result.sources),
                    "has_sufficient_context": result.has_sufficient_context,
                }
            ],
        }

    return rag_agent_node
