"""Tests for the deterministic building blocks: tools, routing, retrieval and escalation rules."""
from agentic.agents.quality_gate import should_escalate
from agentic.agents.supervisor import route_ticket
from agentic.tools import cultpass_tools as cp
from agentic.tools import ticket_tools as tt
from agentic.tools.knowledge_tools import KnowledgeRetriever

BOB, ALICE, EVA = "f556c0", "a4ab87", "f1f10d"
GOOD = {"issue_type": "general_info", "urgency": "low", "confidence": 0.9,
        "requires_account_action": False, "human_requested": False}
KNOWN = {"identified": True, "is_blocked": False}


# --- CultPass tools ---------------------------------------------------------

def test_profile_and_lookup_by_email():
    profile = cp.get_customer_profile(BOB)
    assert profile["subscription"]["tier"] == "premium"
    assert profile["subscription"]["remaining_this_month"] == 4  # quota 6, two reservations
    assert cp.find_customer_by_email("BOB.STONE@granite.com")["user_id"] == BOB
    assert cp.find_customer_by_email("nobody@example.com") is None


def test_reserve_and_cancel_round_trip():
    exp = cp.search_experiences()[-1]
    booked = cp.reserve_experience(BOB, exp["experience_id"])
    assert booked["success"], booked
    assert cp.reserve_experience(BOB, exp["experience_id"])["success"] is False  # no double booking
    cancelled = cp.cancel_reservation(BOB, booked["reservation_id"])
    assert cancelled["success"] and cancelled["credit_returned"]


def test_reservation_business_rules():
    exp = cp.search_experiences()[0]
    assert "blocked" in cp.reserve_experience(ALICE, exp["experience_id"])["error"]
    assert "not active" in cp.reserve_experience(EVA, exp["experience_id"])["error"]


def test_cannot_cancel_someone_elses_reservation():
    alice_res = cp.list_reservations(ALICE)[0]["reservation_id"]
    assert cp.cancel_reservation(BOB, alice_res)["success"] is False


def test_account_tools_are_bound_to_one_customer():
    tools = {t.name: t for t in cp.build_account_tools(BOB, "t-1")}
    assert "user_id" not in tools["cancel_my_reservation"].args
    assert tools["get_my_account"].invoke({})["user_id"] == BOB


def test_subscription_transitions():
    assert cp.manage_subscription(BOB, "pause")["new_status"] == "paused"
    assert cp.manage_subscription(BOB, "pause")["success"] is False
    assert cp.manage_subscription(BOB, "resume")["new_status"] == "active"


# --- Tickets and memory -----------------------------------------------------

def test_ticket_creation_linking_and_memory():
    ticket = tt.get_or_create_ticket("t-new", {"channel": "email"})
    assert ticket["external_user_id"] == "guest" and ticket["status"] == "open"
    uid = tt.link_ticket_to_customer("t-new", BOB, "Bob Stone")
    assert tt.get_or_create_ticket("t-new")["external_user_id"] == BOB

    tt.add_message("t-new", "user", "hello")
    tt.update_ticket_metadata("t-new", status="resolved", issue_type="general_info", tags="a, b")
    tt.update_ticket_metadata("t-new", tags="b, c")
    info = tt.get_or_create_ticket("t-new")
    assert info["status"] == "resolved" and info["tags"] == "a, b, c"

    # Bob's previous ticket and seeded preference are recalled
    prior = tt.get_prior_tickets(uid, exclude_ticket_id="t-new")
    assert prior[0]["ticket_id"] == "past-bob-login"
    assert any("music" in m["content"] for m in tt.get_memories(uid))
    assert tt.save_memory("cultpass", uid, "preference", "Likes jazz", "t-new") is True
    assert tt.save_memory("cultpass", uid, "preference", "Likes jazz", "t-new") is False


# --- Retrieval --------------------------------------------------------------

def test_keyword_retrieval_finds_relevant_articles(monkeypatch):
    import agentic.tools.knowledge_tools as kt
    monkeypatch.setattr(kt, "get_embeddings", lambda: (_ for _ in ()).throw(RuntimeError("offline")))
    retriever = KnowledgeRetriever("cultpass")
    assert retriever.mode == "keyword" and len(retriever.articles) >= 14
    assert retriever.search("I forgot my password and can't log in")[0]["title"] == "How to Handle Login Issues?"
    assert retriever.search("how do refunds work")[0]["title"] == "Refund Policy"
    assert retriever.search("xyzzy quantum") == []


# --- Routing and escalation decisions ----------------------------------------

def test_routing_rules():
    assert route_ticket(GOOD, KNOWN, "open")[0] == "knowledge_agent"
    assert route_ticket({**GOOD, "issue_type": "reservation"}, KNOWN, "open")[0] == "account_agent"
    assert route_ticket({**GOOD, "issue_type": "reservation"}, {"identified": False}, "open")[0] == "request_info"
    assert route_ticket({**GOOD, "human_requested": True}, KNOWN, "open")[0] == "escalation_agent"
    assert route_ticket({**GOOD, "urgency": "critical"}, KNOWN, "open")[0] == "escalation_agent"
    assert route_ticket({**GOOD, "confidence": 0.2}, KNOWN, "open")[0] == "escalation_agent"
    assert route_ticket(GOOD, KNOWN, "escalated")[0] == "escalation_agent"
    blocked = {"identified": True, "is_blocked": True}
    assert route_ticket({**GOOD, "issue_type": "login_access"}, blocked, "open")[0] == "escalation_agent"
    assert route_ticket(GOOD, blocked, "open")[0] == "knowledge_agent"  # general questions are still answered


def test_escalation_rules():
    ok = {"confidence": 0.9, "grounded": True, "needs_human": False}
    assert should_escalate({"assessment": ok})[0] is False
    assert should_escalate({"assessment": {**ok, "confidence": 0.5}})[0] is True
    assert should_escalate({"assessment": {**ok, "grounded": False}})[0] is True
    assert should_escalate({"assessment": {**ok, "needs_human": True}})[0] is True
    refund = [{"tool": "request_refund", "args": {}, "result": {"success": True}}]
    assert should_escalate({"assessment": ok, "actions_taken": refund})[0] is True
