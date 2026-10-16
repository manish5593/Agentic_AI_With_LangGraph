"""End-to-end tests of the LangGraph workflow with a scripted fake LLM (no API key needed).

They exercise the real graph, routing, tools, DB persistence and memory; only the
model's outputs are scripted per scenario.
"""
import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from agentic.agents import (account_agent, classifier, escalation_agent, knowledge_agent,
                            memory_agent, quality_gate)
from agentic.agents.escalation_agent import EscalationHandoff
from agentic.agents.memory_agent import Memory, MemoryExtraction
from agentic.state import ResolutionAssessment, TicketClassification
from agentic.tools import ticket_tools
import agentic.tools.knowledge_tools as kt
from agentic.workflow import build_graph, process_ticket


def classification(**kw):
    base = dict(issue_type="general_info", urgency="low", sentiment="neutral", summary="question",
                requires_account_action=False, human_requested=False, customer_email=None,
                language="English", confidence=0.9)
    return TicketClassification(**{**base, **kw})


GOOD_ASSESSMENT = ResolutionAssessment(confidence=0.9, grounded=True, needs_human=False,
                                       awaiting_customer=False, reason="grounded answer")
HANDOFF = EscalationHandoff(team="general_support", priority="medium", summary="needs a human",
                            steps_taken=["checked KB"], recommended_next_step="call customer",
                            customer_message="A specialist will follow up by email.")


class FakeLLM:
    """Returns scripted objects for structured-output calls and a fixed text otherwise."""

    def __init__(self, outputs):
        self.outputs = outputs  # {schema class: instance}

    def invoke(self, messages):
        return AIMessage(content="Tap 'Forgot Password' on the login screen.")

    def with_structured_output(self, schema):
        fake = self

        class _Runner:
            def invoke(self, messages):
                return fake.outputs[schema]
        return _Runner()


@pytest.fixture
def run(monkeypatch):
    """Configure the fake LLM and return a fresh graph runner."""
    monkeypatch.setattr(kt, "get_embeddings", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    kt._retrievers.clear()

    def configure(**outputs):
        llm = FakeLLM({
            TicketClassification: outputs.get("classification", classification()),
            ResolutionAssessment: outputs.get("assessment", GOOD_ASSESSMENT),
            EscalationHandoff: HANDOFF,
            MemoryExtraction: outputs.get("memories", MemoryExtraction(memories=[])),
        })
        for module in (classifier, knowledge_agent, quality_gate, escalation_agent, memory_agent, account_agent):
            monkeypatch.setattr(module, "get_llm", lambda *a, **k: llm)
        return build_graph(MemorySaver())
    return configure


def test_knowledge_question_is_resolved_with_rag(run):
    graph = run(classification=classification(issue_type="login_access", summary="cannot log in"))
    state = process_ticket("I forgot my password and can't log in", "t-kb", agent=graph)

    assert state["route"] == "knowledge_agent"
    assert state["knowledge"][0]["title"] == "How to Handle Login Issues?"
    assert state["ticket_status"] == "resolved"
    assert "Forgot Password" in state["messages"][-1].content
    roles = [m["role"] for m in ticket_tools.get_ticket_messages("t-kb")]
    assert roles == ["user", "ai"]


def test_low_confidence_resolution_is_escalated(run):
    low = ResolutionAssessment(confidence=0.4, grounded=True, needs_human=False,
                               awaiting_customer=False, reason="unsure")
    graph = run(classification=classification(issue_type="login_access"), assessment=low)
    state = process_ticket("I forgot my password", "t-low", agent=graph)

    assert state["escalation"]["team"] == "general_support"
    assert state["ticket_status"] == "escalated"
    assert state["messages"][-1].content == HANDOFF.customer_message
    assert any("ESCALATION HANDOFF" in m["content"] for m in ticket_tools.get_ticket_messages("t-low"))


def test_blocked_customer_goes_straight_to_escalation(run):
    graph = run(classification=classification(issue_type="login_access"))
    state = process_ticket("I can't log in", "t-blocked", {"external_user_id": "a4ab87"}, agent=graph)
    assert state["route"] == "escalation_agent"
    assert "blocked" in state["route_reason"]


def test_multi_turn_identification_and_short_term_memory(run, monkeypatch):
    graph = run(classification=classification(issue_type="reservation", requires_account_action=True))
    first = process_ticket("Please cancel my reservation", "t-guest", agent=graph)
    assert first["route"] == "request_info"
    assert first["ticket_status"] == "awaiting_customer"

    # Second turn on the same thread: the customer gives their email
    classifier.get_llm().outputs[TicketClassification] = classification(
        issue_type="reservation", requires_account_action=True, customer_email="bob.stone@granite.com")

    def fake_agent(*args, **kwargs):
        class _Agent:
            def invoke(self, payload, config=None):
                call = {"id": "c1", "name": "get_my_reservations", "args": {}}
                return {"messages": [*payload["messages"],
                                     AIMessage(content="", tool_calls=[call]),
                                     ToolMessage(content="[]", tool_call_id="c1"),
                                     AIMessage(content="Which reservation should I cancel?")]}
        return _Agent()
    monkeypatch.setattr(account_agent, "create_react_agent", fake_agent)
    second = process_ticket("It's bob.stone@granite.com", "t-guest", agent=graph)

    assert second["customer"]["name"] == "Bob Stone"
    assert second["route"] == "account_agent"
    assert [a["tool"] for a in second["actions_taken"]] == ["get_my_reservations"]
    # the whole conversation is kept in the thread
    assert len(second["messages"]) == 4
    # long-term memory recalled after identification
    assert any("music" in m for m in second["memories"])
    assert second["prior_tickets"][0]["ticket_id"] == "past-bob-login"


def test_refund_request_forces_escalation_and_memory_is_stored(run, monkeypatch):
    memories = MemoryExtraction(memories=[Memory(category="issue_history", content="Requested a refund for a duplicate charge")])
    graph = run(classification=classification(issue_type="billing_refund", requires_account_action=True),
                memories=memories)

    def fake_agent(*args, tools, **kwargs):
        refund = next(t for t in tools if t.name == "request_refund")

        class _Agent:
            def invoke(self, payload, config=None):
                result = refund.invoke({"reason": "duplicate charge"})
                call = {"id": "r1", "name": "request_refund", "args": {"reason": "duplicate charge"}}
                return {"messages": [*payload["messages"], AIMessage(content="", tool_calls=[call]),
                                     ToolMessage(content=json.dumps(result), tool_call_id="r1"),
                                     AIMessage(content=f"I've registered request {result['refund_request_id']}.")]}
        return _Agent()
    monkeypatch.setattr(account_agent, "create_react_agent", fake_agent)

    state = process_ticket("I was charged twice", "t-refund", {"email": "bob.stone@granite.com"}, agent=graph)
    assert state["route"] == "account_agent"
    assert state["ticket_status"] == "escalated"
    assert "request_refund" in state["escalation"]["reason"]
    texts = [m["content"] for m in ticket_tools.get_ticket_messages("t-refund")]
    assert any(t.startswith("Refund request RF-") for t in texts)
    uid = state["customer"]["udahub_user_id"]
    assert any("duplicate charge" in m["content"] for m in ticket_tools.get_memories(uid))


def test_account_state_memories_are_not_stored(run):
    memories = MemoryExtraction(memories=[
        Memory(category="personal_fact", content="Has a reservation for Samba Night on October 20."),
        Memory(category="preference", content="Prefers replies in Portuguese"),
    ])
    graph = run(classification=classification(issue_type="general_info"), memories=memories)
    state = process_ticket("What's included in my plan?", "t-mem", {"email": "bob.stone@granite.com"}, agent=graph)

    stored = [m["content"] for m in ticket_tools.get_memories(state["customer"]["udahub_user_id"])]
    assert "Prefers replies in Portuguese" in stored
    assert not any("Samba" in m for m in stored)
    assert "(account state)" in state["trace"][-1]
