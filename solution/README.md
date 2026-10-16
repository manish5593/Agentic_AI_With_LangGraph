# UDA-Hub: Reference Solution

This folder contains the complete, working UDA-Hub project for reviewers. UDA-Hub is a LangGraph multi-agent
system that resolves customer support tickets for CultPass. It classifies each ticket, routes it to the right
agent, and then either resolves it (with RAG and account tools) or escalates it to a human. It uses short- and
long-term memory throughout.

The full architecture, routing rules and memory design are in [`agentic/design/README.md`](agentic/design/README.md).

## How a ticket flows

```
load_context → classifier → supervisor ─┬─> knowledge_agent (RAG) ──┐
                                        ├─> account_agent (tools) ──┴─> quality_gate ─┬─> approve ─────────┐
                                        ├─> escalation_agent <────────────────────────┘                    │
                                        └─> request_info ──────────────────────────────────────────────────┤
                                                              write_memory <── finalize <──────────────────┘
```

| Agent | What it does |
|---|---|
| **Classifier** | Gives the ticket a structured classification: issue type, urgency, sentiment, language, whether account action is needed, and confidence |
| **Supervisor** | Identifies the customer (from metadata or an email in the conversation) and routes the ticket with deterministic rules |
| **Knowledge agent** | Answers how-to and policy questions with RAG over the 18 knowledge base articles |
| **Account agent** | A ReAct agent with CultPass tools bound to the current customer: account, reservations, booking, cancellation, subscription changes and refund requests |
| **Quality gate** | Scores the draft reply for confidence and checks that it is backed by the articles or tool results. It escalates on low confidence (< 0.7), an unsupported draft, or a policy that needs a human (such as a refund) |
| **Escalation agent** | Picks the human team and priority, saves a handoff note on the ticket, and replies to the customer |
| **Memory** | Short-term: the conversation per ticket thread (`MemorySaver`). Long-term: customer preferences (`customer_memory` table) and previous tickets in `udahub.db` |

## Running it

From the repository root:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd solution
cp .env.example .env        # add OPENAI_API_KEY (and OPENAI_BASE_URL if using Vocareum)
```

1. `01_external_db_setup.ipynb` builds `data/external/cultpass.db`. This is optional: the database is already included.
2. `02_core_db_setup.ipynb` builds `data/core/udahub.db`. This is also optional, since the database is included.
3. `03_agentic_app.ipynb` runs the demo scenarios, then an interactive chat (`chat_interface(orchestrator, "1")`).

Re-run notebooks 01 and 02 to reset the databases after the demos, because the demos make real bookings and cancellations.

## Demo scenarios (notebook 03)

| # | Ticket | Expected path |
|---|---|---|
| 1 | Guest asks what a subscription includes | classifier → knowledge_agent (RAG) → resolved |
| 2 | Cathy asks about her reservations, then "cancel that one" | account_agent with tools, and the follow-up relies on short-term memory |
| 3 | Guest asks to book Samba Night, then gives their email | request_info → customer identified → account_agent |
| 4 | Alice (blocked account) can't log in | supervisor → escalation to Trust & Safety, without revealing why the account is blocked |
| 5 | Frank was charged twice | account_agent → `request_refund` → escalation for support-lead approval |
| 6 | Bob still can't log in | His previous login ticket is recalled from long-term memory, the documented fix has already failed, and the ticket is escalated |
| 7 | Bob asks for a recommendation | Uses his stored preference (music and dance in Rio) |
| 8 | Customer demands a human | Escalated immediately |

## Tests

These need no API key. They use a scripted fake LLM and temporary copies of the databases.

```bash
python -m pytest tests
```

- `tests/test_tools.py` covers:
  - the tool business rules: blocked accounts, inactive subscriptions, double booking, ownership, quota and subscription transitions
  - account tools bound to one customer
  - ticket and memory persistence
  - keyword retrieval
  - every routing and escalation rule
- `tests/test_workflow.py` runs the whole graph end to end through these paths:
  - RAG resolution
  - low-confidence escalation
  - a blocked customer
  - multi-turn identification, recalling both short-term and long-term memory
  - a refund request that forces escalation and writes a new memory

## Folder guide

| Path | Contents |
|---|---|
| `agentic/workflow.py` | The LangGraph graph (`orchestrator`) and `process_ticket()` |
| [`agentic/agents/`](agentic/agents/README.md) | Classifier, supervisor, knowledge and account resolvers, quality gate, escalation, memory |
| [`agentic/tools/`](agentic/tools/README.md) | CultPass account tools, RAG retriever, ticket and memory storage |
| [`agentic/design/`](agentic/design/README.md) | Architecture, routing rules and memory design |
| `agentic/config.py` | Models, database paths and decision thresholds |
| `agentic/state.py` | Graph state and structured-output schemas |
| [`data/core/`](data/core/README.md) | `udahub.db`: tables, ticket statuses and demo data |
| [`data/external/`](data/external/README.md) | `cultpass.db`, the JSONL seed data and the demo customers |
| `data/models/` | SQLAlchemy models for both databases |
| `tests/` | Unit tests and end-to-end graph tests |
| `utils.py` | Starter helpers, including `chat_interface` |

The project overview for the whole repository is in the [root README](../README.md).

## Where to find each requirement

| Requirement | Location |
|---|---|
| Multi-agent architecture with LangGraph | `agentic/workflow.py`, `agentic/agents/` |
| Input handling (text and metadata) | `process_ticket()` in `agentic/workflow.py`, `load_context` in `agentic/agents/memory_agent.py` |
| Classification and routing | `agentic/agents/classifier.py`, `agentic/agents/supervisor.py` |
| RAG over the knowledge base | `agentic/tools/knowledge_tools.py`, `agentic/agents/knowledge_agent.py` |
| Tools, including the internal refund tool | `agentic/tools/cultpass_tools.py` |
| Resolve or escalate | `agentic/agents/quality_gate.py`, `agentic/agents/escalation_agent.py` |
| Memory: state, short-term and long-term | `agentic/state.py`, `agentic/agents/memory_agent.py`, `agentic/tools/ticket_tools.py`, `CustomerMemory` in `data/models/udahub.py` |
| At least 14 knowledge articles | `data/external/cultpass_articles.jsonl` (18 articles) |
| Configuration and thresholds | `agentic/config.py` (overridable with env vars) |
