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

The architecture, routing rules and memory design are described in
[`starter/agentic/design/README.md`](starter/agentic/design/README.md).

## Getting Started

### Dependencies

Python 3.11+ and an OpenAI API key. Python packages are listed in `requirements.txt`: LangGraph, LangChain, langchain-openai, SQLAlchemy, python-dotenv and pytest.

### Installation

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp starter/.env.example starter/.env   # then add your OPENAI_API_KEY
```

Then run the notebooks in `starter/` in order:

1. `01_external_db_setup.ipynb` creates `data/external/cultpass.db` (customers, subscriptions, experiences, reservations)
2. `02_core_db_setup.ipynb` creates `data/core/udahub.db` (account, 18 knowledge articles, tickets, demo history and memory)
3. `03_agentic_app.ipynb` runs the demo scenarios and an interactive chat

Programmatic use (from `starter/`):

```python
from agentic.workflow import orchestrator, process_ticket
state = process_ticket("I'd like to cancel my reservation", "T-1", {"email": "cathy.bloom@florals.org"})
print(state["final_response"])
```

## Testing

From `starter/` (after running notebooks 01 and 02):

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

| Deliverable | Where |
|---|---|
| Multi-agent architecture (Supervisor, Classifier, Resolvers, Escalation) | `starter/agentic/agents/`, `starter/agentic/workflow.py` |
| Architecture design | `starter/agentic/design/README.md` |
| Input handling (text + metadata) | `process_ticket(...)`, `load_context` |
| Routing, RAG, resolve or escalate | `supervisor.py`, `knowledge_agent.py`, `quality_gate.py` |
| Tools (incl. internal refund tool) | `starter/agentic/tools/` |
| Memory (state, short-term, long-term) | `memory_agent.py`, `ticket_tools.py`, `CustomerMemory` model |
| Knowledge base (≥ 14 articles) | `starter/data/external/cultpass_articles.jsonl` (18) |
| Demo | `starter/03_agentic_app.ipynb` |

## Built With

* [LangGraph](https://langchain-ai.github.io/langgraph/) - Agent orchestration, state and checkpointing
* [LangChain](https://python.langchain.com/) - Tools, vector store and model integrations
* [OpenAI](https://platform.openai.com/) - `gpt-4o-mini` chat model and `text-embedding-3-small` embeddings
* [SQLAlchemy](https://www.sqlalchemy.org/) - Core (`udahub.db`) and external (`cultpass.db`) databases

## License
[License](../LICENSE.md)
