# Agents

Each module provides one or more LangGraph nodes, which `agentic/workflow.py` wires into the graph. A node reads the
shared `UdaHubState` and returns the fields it changes. Every node also adds a line to `state["trace"]`, so each
decision can be audited. The full flow and routing rules are in [`../design/README.md`](../design/README.md).

| Module | Node(s) | Uses the LLM | What it does |
|---|---|---|---|
| `memory_agent.py` | `load_context` | No | Runs first on every turn. It resolves the ticket from `thread_id`, creating it if needed, and identifies the customer from metadata. It stores the inbound message, recalls long-term memory (preferences and previous tickets), and resets the per-turn fields. |
| `classifier.py` | `classifier` | Yes, structured output | Produces a `TicketClassification`: issue type (11 categories), urgency, sentiment, language, whether account action is needed, whether a human was requested, any email mentioned, and confidence. Recommendations count as account work, because they need the real catalog. |
| `supervisor.py` | `supervisor`, `request_info` | No | Links a guest ticket to a customer when the classifier found their email, then routes with `route_ticket()`, a pure function of the classification, customer and ticket status. `request_info` asks a guest for their email when an account action is needed. |
| `knowledge_agent.py` | `knowledge_agent` | Yes | Retrieves the top 3 relevant knowledge base articles and answers using only those, in the customer's language. With no article above the score threshold, it produces no draft, and the ticket is escalated. |
| `account_agent.py` | `account_agent` | Yes, ReAct agent | A `create_react_agent` with the CultPass tools bound to the current customer, plus knowledge base search. The prompt has it look IDs up before acting and ask a clarifying question when the request is ambiguous, and it never promises a refund. It records every tool call in `actions_taken`. |
| `quality_gate.py` | `quality_gate`, `approve` | Yes, structured output | Scores the draft against the evidence (articles or tool results) for confidence, grounding, whether a human is needed and whether it waits on the customer. `should_escalate()` then decides in plain code. It escalates if a refund was requested, a human is needed, the draft isn't supported by the evidence, or confidence is below 0.7. |
| `escalation_agent.py` | `escalation_agent` | Yes, structured output | Picks the team (Trust & Safety, billing, technical support, privacy/legal or general support) and the priority. It saves a handoff note on the ticket and writes an empathetic reply. It never reveals why an account is blocked and never promises an outcome. |
| `memory_agent.py` | `finalize`, `write_memory` | `write_memory` only | `finalize` sends the reply, logs it and sets the ticket status (`resolved`, `awaiting_customer` or `escalated`). `write_memory` extracts durable facts about an identified customer, as described below. |
| `common.py` | | No | Shared helpers for traces, the session's conversation, and the customer-context block used in prompts. |

## Long-term memory rules (`write_memory`)

The LLM proposes memories, and code then decides what is stored:

- **Wording:** the prompt asks for third-person summaries of what the customer said themselves, for example "Reported <problem> (<outcome>)". It never asks for quotes, inferences or facts from account data.
- **Filter:** `drop_reason()` rejects memories about reservations, bookings, cancellations or quota, because the system can look these up live and they go stale. Preferences are exempt. It also rejects one-off requests, such as asking to talk to a real person.
- **Duplicates:** `save_memory()` in `../tools/ticket_tools.py` ignores case, punctuation and spacing when it checks for an existing memory.
- **Trace:** the trace lists what was stored and what was dropped, and why.
