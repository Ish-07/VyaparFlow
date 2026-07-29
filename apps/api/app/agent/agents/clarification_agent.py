"""
Clarification agent: reached when the supervisor decided it can't route
safely - low confidence, unknown intent, or missing required entities.
final_response is already set by the supervisor node; this agent's job
is just to formally set status=NEEDS_CONFIRMATION as its own graph step,
keeping the state transition explicit and traceable rather than implicit.
"""
from app.agent.state import AgentState


async def clarification_agent_node(state: AgentState) -> dict:
    return {
        "status": "NEEDS_CONFIRMATION",
        "tool_results": [{"agent": "clarification_agent", "tool": None, "status": "NEEDS_CONFIRMATION"}],
    }
