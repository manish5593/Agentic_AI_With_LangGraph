"""Memory nodes.

* `load_context` runs first on every turn: it resolves the ticket and customer, stores the
  inbound message, and recalls long-term memory (preferences + previous tickets).
* `write_memory` runs last: it persists the reply and extracts durable customer facts.

Short-term memory (the session's conversation) is kept by the LangGraph checkpointer,
keyed by `thread_id` (= ticket id).
"""
from typing import Literal

from langchain_core.messages import AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from agentic import config as cfg
from agentic.agents.common import add_trace, conversation_text, last_user_message
from agentic.llm import get_llm
from agentic.tools import cultpass_tools, ticket_tools


def build_customer(ticket: dict) -> dict:
    base = {
        "account_id": ticket["account_id"],
        "udahub_user_id": ticket["udahub_user_id"],
        "external_user_id": ticket["external_user_id"],
        "name": ticket["user_name"],
        "identified": False,
    }
    if ticket["external_user_id"] == cfg.GUEST_EXTERNAL_USER_ID:
        return base
    profile = cultpass_tools.get_customer_profile(ticket["external_user_id"])
    if profile is None:
        return base
    return {
        **base,
        "name": profile["name"],
        "email": profile["email"],
        "is_blocked": profile["is_blocked"],
        "subscription": profile["subscription"],
        "identified": True,
    }


def recall(customer: dict, ticket_id: str) -> dict:
    """Long-term memory lookup for an identified customer."""
    if not customer.get("identified"):
        return {"memories": [], "prior_tickets": []}
    uid = customer["udahub_user_id"]
    return {
        "memories": [f"({m['category']}) {m['content']}" for m in ticket_tools.get_memories(uid)],
        "prior_tickets": ticket_tools.get_prior_tickets(uid, exclude_ticket_id=ticket_id),
    }


def load_context(state: dict, config: RunnableConfig) -> dict:
    ticket_id = state.get("ticket_id") or config["configurable"]["thread_id"]
    metadata = dict(state.get("metadata") or {})

    # Metadata may identify the customer by email instead of id
    if metadata.get("email") and not metadata.get("external_user_id"):
        profile = cultpass_tools.find_customer_by_email(metadata["email"])
        if profile:
            metadata.update(external_user_id=profile["user_id"], user_name=profile["name"])

    # `customer` is only set by this node, so its absence means a new session
    first_turn = not state.get("customer")
    ticket = ticket_tools.get_or_create_ticket(ticket_id, metadata)
    # Messages stored on the ticket before this session started (e.g. created by another channel)
    history = ticket_tools.get_ticket_messages(ticket_id) if first_turn else state.get("ticket_history", [])

    user_text = last_user_message(state)
    if user_text:
        ticket_tools.add_message(ticket_id, "user", user_text)

    customer = build_customer(ticket)
    entry = (f"[memory] ticket={ticket_id} customer={customer.get('name')} "
             f"identified={customer['identified']} status={ticket['status']}")
    return {
        "ticket_id": ticket_id,
        "metadata": metadata,
        "channel": ticket["channel"],
        "ticket_status": ticket["status"],
        "ticket_history": history,
        "customer": customer,
        **recall(customer, ticket_id),
        # reset per-turn fields
        "classification": {},
        "route": None,
        "route_reason": "",
        "knowledge": [],
        "draft_response": None,
        "resolver": None,
        "actions_taken": [],
        "assessment": {},
        "escalation": None,
        "final_response": "",
        "trace": add_trace({}, entry),  # trace is per turn
    }


def finalize(state: dict) -> dict:
    """Send the reply: add it to the conversation, persist it and update ticket metadata."""
    reply = state["final_response"]
    ticket_id = state["ticket_id"]
    ticket_tools.add_message(ticket_id, "ai", reply)

    if state.get("escalation"):
        status = "escalated"
    elif state.get("route") == "request_info" or state.get("assessment", {}).get("awaiting_customer"):
        status = "awaiting_customer"
    else:
        status = "resolved"
    issue_type = state.get("classification", {}).get("issue_type")
    tags = ", ".join(t for t in [issue_type, state.get("resolver")] if t)
    ticket_tools.update_ticket_metadata(ticket_id, status=status, issue_type=issue_type, tags=tags)
    return {
        "messages": [AIMessage(content=reply)],
        "ticket_status": status,
        "trace": add_trace(state, f"[finalize] status={status}"),
    }


class Memory(BaseModel):
    category: Literal["preference", "personal_fact", "issue_history"]
    content: str = Field(description="Self-contained statement, e.g. 'Prefers replies in Portuguese'.")


class MemoryExtraction(BaseModel):
    memories: list[Memory] = Field(
        default_factory=list,
        description="New durable facts worth remembering for future tickets. Empty if none.",
    )


MEMORY_PROMPT = """You maintain long-term memory about a customer of a cultural-experiences subscription service.
From the latest exchange, extract ONLY durable information useful in future support tickets:
- preferences (language, contact channel, favourite kinds of experiences or cities, accessibility needs)
- personal facts relevant to support (e.g. 'travels often to Rio', 'shares the account with partner')
- important issue history (e.g. 'requested a refund for a duplicate charge in this ticket')
Do NOT store secrets, passwords, payment data, or one-off details. Do not repeat known memories.
Return an empty list when there is nothing new.

Known memories:
{known}

Latest exchange:
{exchange}"""


def write_memory(state: dict) -> dict:
    customer = state.get("customer") or {}
    if not customer.get("identified"):
        return {"trace": add_trace(state, "[memory] guest customer: nothing stored")}
    extractor = get_llm().with_structured_output(MemoryExtraction)
    result: MemoryExtraction = extractor.invoke([
        SystemMessage(content=MEMORY_PROMPT.format(
            known="\n".join(state.get("memories") or []) or "(none)",
            exchange=conversation_text(state),
        ))
    ])
    stored = [
        m.content for m in result.memories
        if ticket_tools.save_memory(
            customer["account_id"], customer["udahub_user_id"], m.category, m.content, state["ticket_id"]
        )
    ]
    return {"trace": add_trace(state, f"[memory] stored {len(stored)} new memories: {stored}")}
