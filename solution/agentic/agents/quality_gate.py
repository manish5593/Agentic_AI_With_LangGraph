"""Quality gate: decides whether a draft answer is good enough to send or must be escalated."""
import json

from langchain_core.messages import HumanMessage, SystemMessage

from agentic import config
from agentic.agents.common import add_trace, conversation_text
from agentic.llm import get_llm
from agentic.state import ResolutionAssessment
from agentic.tools.cultpass_tools import ESCALATING_TOOLS
from agentic.tools.knowledge_tools import format_articles

GATE_PROMPT = """You review draft replies written by an AI support agent for CultPass before they are sent.
Judge the draft against the evidence (knowledge base articles and tool results) only.
- confidence: how sure you are that the draft correctly and fully addresses the customer's request.
- grounded: false if the draft states facts, policies or account details not supported by the evidence.
- needs_human: true if policy requires a human (refund approval, blocked account, identity verification,
  legal/data-protection issues), if the draft says it cannot help, or if the issue is persistent
  after the documented steps were already tried (see conversation / previous tickets).
- awaiting_customer: true if the draft asks a clarifying question that is genuinely needed to proceed.
  A good clarifying question is a valid outcome and deserves high confidence."""


def assess_resolution(state: dict) -> dict:
    draft = state.get("draft_response")
    if not draft:
        assessment = {"confidence": 0.0, "grounded": False, "needs_human": True,
                      "awaiting_customer": False, "reason": "resolver could not produce an answer"}
        return {"assessment": assessment,
                "trace": add_trace(state, f"[quality_gate] {assessment['reason']}")}

    evidence = []
    if state.get("knowledge"):
        evidence.append("Knowledge base:\n" + format_articles(state["knowledge"]))
    if state.get("actions_taken"):
        evidence.append("Tool calls and results:\n" + json.dumps(state["actions_taken"], indent=1, default=str))
    if state.get("prior_tickets"):
        evidence.append("Previous tickets:\n" + json.dumps(state["prior_tickets"], indent=1, default=str))

    result: ResolutionAssessment = get_llm().with_structured_output(ResolutionAssessment).invoke([
        SystemMessage(content=GATE_PROMPT),
        HumanMessage(content=f"Conversation:\n{conversation_text(state)}\n\n"
                             f"{chr(10).join(evidence) or 'No evidence.'}\n\nDraft reply:\n{draft}"),
    ])
    assessment = result.model_dump()
    return {"assessment": assessment, "trace": add_trace(
        state, f"[quality_gate] confidence={assessment['confidence']:.2f} grounded={assessment['grounded']} "
               f"needs_human={assessment['needs_human']}: {assessment['reason']}")}


def should_escalate(state: dict) -> tuple[bool, str]:
    """Deterministic resolve-vs-escalate decision on top of the gate's assessment."""
    a = state.get("assessment") or {}
    used = {x["tool"] for x in state.get("actions_taken", [])
            if isinstance(x.get("result"), dict) and x["result"].get("success")}
    if used & ESCALATING_TOOLS:
        return True, f"policy requires human approval for {sorted(used & ESCALATING_TOOLS)}"
    if a.get("needs_human"):
        return True, a.get("reason", "human required")
    if not a.get("grounded", False):
        return True, "draft is not grounded in the knowledge base or account data"
    if a.get("confidence", 0) < config.RESOLUTION_MIN_CONFIDENCE:
        return True, f"resolution confidence {a.get('confidence', 0):.2f} below {config.RESOLUTION_MIN_CONFIDENCE}"
    return False, "draft approved"


def approve(state: dict) -> dict:
    return {"final_response": state["draft_response"],
            "trace": add_trace(state, "[quality_gate] approved draft")}
