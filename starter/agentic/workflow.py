"""UDA-Hub orchestration graph.

    START -> load_context -> classifier -> supervisor ─┬─> knowledge_agent ─┐
                                                       ├─> account_agent ───┴─> quality_gate ─┬─> approve ──────────┐
                                                       ├─> escalation_agent <─────────────────┘                     │
                                                       └─> request_info ────────────────────────────────────────────┤
                                     END <- write_memory <- finalize <──────────────────────────────────────────────┘

See agentic/design/README.md for the full architecture.
"""
from typing import Optional

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agentic.agents.account_agent import resolve_with_account_tools
from agentic.agents.classifier import classify
from agentic.agents.escalation_agent import escalate
from agentic.agents.knowledge_agent import resolve_with_knowledge
from agentic.agents.memory_agent import finalize, load_context, write_memory
from agentic.agents.quality_gate import approve, assess_resolution, should_escalate
from agentic.agents.supervisor import request_info, supervise
from agentic.state import UdaHubState


def _after_supervisor(state: UdaHubState) -> str:
    return state["route"]


def _after_quality_gate(state: UdaHubState) -> str:
    escalate_, _ = should_escalate(state)
    return "escalation_agent" if escalate_ else "approve"


def build_graph(checkpointer=None):
    graph = StateGraph(UdaHubState)

    graph.add_node("load_context", load_context)
    graph.add_node("classifier", classify)
    graph.add_node("supervisor", supervise)
    graph.add_node("knowledge_agent", resolve_with_knowledge)
    graph.add_node("account_agent", resolve_with_account_tools)
    graph.add_node("quality_gate", assess_resolution)
    graph.add_node("approve", approve)
    graph.add_node("escalation_agent", escalate)
    graph.add_node("request_info", request_info)
    graph.add_node("finalize", finalize)
    graph.add_node("write_memory", write_memory)

    graph.add_edge(START, "load_context")
    graph.add_edge("load_context", "classifier")
    graph.add_edge("classifier", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _after_supervisor,
        ["knowledge_agent", "account_agent", "escalation_agent", "request_info"],
    )
    graph.add_edge("knowledge_agent", "quality_gate")
    graph.add_edge("account_agent", "quality_gate")
    graph.add_conditional_edges("quality_gate", _after_quality_gate, ["approve", "escalation_agent"])
    for node in ("approve", "escalation_agent", "request_info"):
        graph.add_edge(node, "finalize")
    graph.add_edge("finalize", "write_memory")
    graph.add_edge("write_memory", END)

    return graph.compile(checkpointer=checkpointer if checkpointer is not None else MemorySaver())


orchestrator = build_graph()


def process_ticket(text: str, ticket_id: str, metadata: Optional[dict] = None, agent=None) -> dict:
    """Send one customer message (plus optional ticket metadata) through the system.

    `metadata` can include: account_id, external_user_id or email, user_name, channel, urgency, tags.
    Returns the final state for this turn.
    """
    agent = agent or orchestrator
    payload = {"messages": [HumanMessage(content=text)]}
    if metadata:
        payload["metadata"] = metadata
    return agent.invoke(payload, config={"configurable": {"thread_id": ticket_id}})
