# UDA-Hub: Starter Workspace

This is the project workspace. It contains the UDA-Hub multi-agent support system built on the course starter
code. The same code is in `../solution/` for reviewers.

- Project overview, setup, tests and full demo results: [`../README.md`](../README.md)
- Architecture, routing rules and memory design: [`agentic/design/README.md`](agentic/design/README.md)

## Quick start

From the repository root, after `pip install -r requirements.txt`:

```bash
cd starter
cp .env.example .env          # add OPENAI_API_KEY (and OPENAI_BASE_URL if using Vocareum)
python -m pytest tests        # offline tests, no API key needed
```

Both databases are included, so you can open `03_agentic_app.ipynb` straight away. It runs 8 demo scenarios
and then an interactive chat. The other two notebooks rebuild the databases, so run them only to reset the
data after the demos:

1. `01_external_db_setup.ipynb` rebuilds the CultPass database
2. `02_core_db_setup.ipynb` rebuilds the UDA-Hub database

## Demo results

`03_agentic_app.ipynb` is committed with the outputs of a run against the real model (`gpt-4o-mini`), so you can
read each scenario's decision trace and reply without running it.

| # | Ticket | Outcome |
|---|---|---|
| 1 | Guest asks what a subscription includes | Answered from the knowledge base (RAG) |
| 2 | Cathy lists her reservations, then cancels one | Account agent looks it up, then cancels it |
| 3 | Guest asks to book, then gives their email | Customer identified; the agent finds the booking already exists |
| 4 | Blocked customer can't log in | Escalated to Trust & Safety |
| 5 | Customer charged twice | Refund request registered and escalated to billing |
| 6 | Login still failing after a reset | Escalated to technical support |
| 7 | Customer asks for a recommendation | Real catalog experiences matching their stored preference |
| 8 | Customer demands a human | Escalated immediately |

The [root README](../README.md#demo-results) has the full table, with the tools each agent used and what was
stored in long-term memory.

## Folder guide

| Path | Contents |
|---|---|
| `agentic/workflow.py` | The LangGraph graph (`orchestrator`) and `process_ticket()` |
| [`agentic/agents/`](agentic/agents/README.md) | Classifier, supervisor, knowledge and account resolvers, quality gate, escalation, memory |
| [`agentic/tools/`](agentic/tools/README.md) | CultPass account tools, RAG retriever, ticket and memory storage |
| `agentic/config.py` | Models, database paths and decision thresholds |
| `agentic/state.py` | Graph state and structured-output schemas |
| [`agentic/design/`](agentic/design/README.md) | Architecture diagram, Mermaid graph and design document |
| [`data/core/`](data/core/README.md) | `udahub.db`: tickets, knowledge base, long-term memory |
| [`data/external/`](data/external/README.md) | `cultpass.db` and the JSONL seed data |
| `data/models/` | SQLAlchemy models for both databases |
| `tests/` | Unit tests and end-to-end graph tests |
| `utils.py` | Starter helpers, including `chat_interface` |
