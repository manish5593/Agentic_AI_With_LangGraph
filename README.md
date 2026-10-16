# UDA-Hub: Multi-Agent Customer Support with LangGraph

UDA-Hub is an intelligent, multi-agent decision suite that resolves customer support tickets for the
platforms it serves. It is built with LangGraph. The first integrated account is **CultPass**, a
subscription for cultural experiences.

A ticket in natural language, plus optional metadata (customer, channel, urgency), goes through these agents:

- **Classifier**: issue type, urgency, sentiment, language and confidence
- **Supervisor**: identifies the customer and routes the ticket with auditable rules
- **Knowledge agent**: answers from the knowledge base with RAG
- **Account agent**: uses CultPass tools (reservations, subscription, refund requests) scoped to the customer
- **Quality gate**: approves the answer or escalates it, based on confidence, grounding and policy
- **Escalation agent**: hands off to the right human team with a summary
- **Memory**: short-term (the session's conversation, via the checkpointer) and long-term (preferences and
  past tickets, in `udahub.db`)

## Repository layout

| Folder | Contents |
|---|---|
| `starter/` | The project workspace, with the implementation built on the course starter code |
| `solution/` | A self-contained copy of the working project for reviewers, with its own guide in [`solution/README.md`](solution/README.md) |
| `requirements.txt` | Python dependencies shared by both folders |

The two folders hold the same code, and each runs on its own: paths are resolved relative to the folder.
The architecture, routing rules and memory design are described in
[`solution/agentic/design/README.md`](solution/agentic/design/README.md).

```
<starter|solution>/
├── 01_external_db_setup.ipynb   # builds data/external/cultpass.db
├── 02_core_db_setup.ipynb       # builds data/core/udahub.db
├── 03_agentic_app.ipynb         # demo scenarios and interactive chat
├── agentic/
│   ├── workflow.py              # LangGraph graph: `orchestrator`, `process_ticket()`
│   ├── agents/                  # classifier, supervisor, resolvers, quality gate, escalation, memory
│   ├── tools/                   # CultPass tools, RAG retriever, ticket and memory storage
│   ├── design/README.md         # architecture
│   ├── config.py                # models, paths and thresholds
│   └── state.py                 # graph state and structured-output schemas
├── data/                        # SQLAlchemy models, JSONL seed data and the SQLite databases
└── tests/                       # offline unit and end-to-end tests
```

## Getting Started

### Dependencies

Python 3.11+ and an OpenAI API key. Python packages are listed in `requirements.txt`: LangGraph, LangChain, langchain-openai, SQLAlchemy, python-dotenv and pytest.

### Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd solution                   # or starter
cp .env.example .env          # then add your OPENAI_API_KEY (and OPENAI_BASE_URL if using Vocareum)
```

Then run the notebooks in order:

1. `01_external_db_setup.ipynb` creates `data/external/cultpass.db` (customers, subscriptions, experiences, reservations)
2. `02_core_db_setup.ipynb` creates `data/core/udahub.db` (account, 18 knowledge articles, tickets, demo history and memory)
3. `03_agentic_app.ipynb` runs 8 demo scenarios and an interactive chat

Both databases are committed, so steps 1 and 2 are only needed to reset the data. The demos make real
bookings and cancellations, so re-run them after the demos to start fresh.

Programmatic use (from `solution/` or `starter/`):

```python
from agentic.workflow import orchestrator, process_ticket
state = process_ticket("I'd like to cancel my reservation", "T-1", {"email": "cathy.bloom@florals.org"})
print(state["final_response"])
```

## Testing

From `solution/` or `starter/`:

```bash
python -m pytest tests
```

The tests need no API key. Each one runs against a temporary copy of the databases, so your data is not modified.

### Break Down Tests

- `tests/test_tools.py` covers the deterministic building blocks:
  - CultPass tool business rules: blocked accounts, inactive subscriptions, double booking, ownership checks, quota and subscription state transitions
  - account tools that are bound to one customer
  - ticket creation and linking, metadata and long-term memory
  - keyword retrieval quality
  - every routing rule and escalation rule
- `tests/test_workflow.py` runs the whole LangGraph workflow end to end with a scripted fake LLM:
  - a RAG resolution
  - a low-confidence answer that gets escalated
  - a blocked customer who is escalated straight away
  - a multi-turn guest who is identified by email, with short-term and long-term memory recall
  - a refund request that forces escalation and stores a new memory

## Project Instructions

Paths are relative to `solution/` (the same files exist in `starter/`).

| Deliverable | Where |
|---|---|
| Multi-agent architecture (Supervisor, Classifier, Resolvers, Escalation) | `agentic/agents/`, `agentic/workflow.py` |
| Architecture design | `agentic/design/README.md` |
| Input handling (text + metadata) | `process_ticket(...)`, `load_context` |
| Routing, RAG, resolve or escalate | `supervisor.py`, `knowledge_agent.py`, `quality_gate.py` |
| Tools (incl. internal refund tool) | `agentic/tools/` |
| Memory (state, short-term, long-term) | `memory_agent.py`, `ticket_tools.py`, `CustomerMemory` model |
| Knowledge base (≥ 14 articles) | `data/external/cultpass_articles.jsonl` (18) |
| Demo | `03_agentic_app.ipynb` |

## Built With

* [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent orchestration, state and checkpointing
* [LangChain](https://python.langchain.com/) - Tools, vector store and model integrations
* [OpenAI](https://platform.openai.com/) - `gpt-4o-mini` chat model and `text-embedding-3-small` embeddings
* [SQLAlchemy](https://www.sqlalchemy.org/) - Core (`udahub.db`) and external (`cultpass.db`) databases
