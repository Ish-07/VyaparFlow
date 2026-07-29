"""
Builds the VyaparFlow agent graph.

    supervisor
       |
       +--> inventory_agent -----------------------------> END
       +--> finance_agent --(sale_completed?)--> advisor_agent --> END
       |                  \\--(no)---------------------------> END
       +--> clarification_agent ---------------------------> END

A fresh graph is built per call (see build_agent_graph(session)) because
every node needs the current request's DB session closed over it, and a
session is request-scoped, not something that can be baked into a
module-level singleton graph. Compiling a handful of nodes has
negligible overhead compared to the DB/LLM calls the nodes themselves
make.
"""
from langgraph.graph import END, StateGraph

from app.agent.agents.advisor_agent import build_advisor_agent
from app.agent.agents.clarification_agent import clarification_agent_node
from app.agent.agents.finance_agent import build_finance_agent
from app.agent.agents.inventory_agent import build_inventory_agent
from app.agent.agents.rag_agent import build_rag_agent
from app.agent.agents.supervisor import supervisor_node
from app.agent.state import AgentState


def _route_from_supervisor(state: AgentState) -> str:
    return state.get("next_agent", "clarification_agent")


def _route_from_finance(state: AgentState) -> str:
    return "advisor_agent" if state.get("sale_completed") else "__end__"


def build_agent_graph(session):
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("inventory_agent", build_inventory_agent(session))
    graph.add_node("finance_agent", build_finance_agent(session))
    graph.add_node("advisor_agent", build_advisor_agent(session))
    graph.add_node("clarification_agent", clarification_agent_node)
    graph.add_node("rag_agent", build_rag_agent(session))

    graph.set_entry_point("supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "inventory_agent": "inventory_agent",
            "finance_agent": "finance_agent",
            "clarification_agent": "clarification_agent",
            "rag_agent": "rag_agent",
        },
    )
    graph.add_conditional_edges(
        "finance_agent",
        _route_from_finance,
        {"advisor_agent": "advisor_agent", "__end__": END},
    )
    graph.add_edge("inventory_agent", END)
    graph.add_edge("advisor_agent", END)
    graph.add_edge("clarification_agent", END)
    graph.add_edge("rag_agent", END)

    return graph.compile()
