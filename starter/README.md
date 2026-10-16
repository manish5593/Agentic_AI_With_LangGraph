# UDA-Hub: Starter Workspace

This is the project workspace. It contains the UDA-Hub multi-agent support system built on the course starter
code. The same code is in `../solution/` for reviewers.

- Project overview, setup and tests: [`../README.md`](../README.md)
- Architecture, routing rules and memory design: [`agentic/design/README.md`](agentic/design/README.md)

## Quick start

From the repository root, after `pip install -r requirements.txt`:

```bash
cd starter
cp .env.example .env          # add OPENAI_API_KEY (and OPENAI_BASE_URL if using Vocareum)
python -m pytest tests        # offline tests, no API key needed
```

Then open the notebooks in order:

1. `01_external_db_setup.ipynb` builds the CultPass database
2. `02_core_db_setup.ipynb` builds the UDA-Hub database
3. `03_agentic_app.ipynb` runs the demo scenarios and an interactive chat

## Folder guide

| Path | Contents |
|---|---|
| `agentic/workflow.py` | The LangGraph graph (`orchestrator`) and `process_ticket()` |
| [`agentic/agents/`](agentic/agents/README.md) | Classifier, supervisor, knowledge and account resolvers, quality gate, escalation, memory |
| [`agentic/tools/`](agentic/tools/README.md) | CultPass account tools, RAG retriever, ticket and memory storage |
| `agentic/config.py` | Models, database paths and decision thresholds |
| `agentic/state.py` | Graph state and structured-output schemas |
| [`data/core/`](data/core/README.md) | `udahub.db`: tickets, knowledge base, long-term memory |
| [`data/external/`](data/external/README.md) | `cultpass.db` and the JSONL seed data |
| `data/models/` | SQLAlchemy models for both databases |
| `tests/` | Unit tests and end-to-end graph tests |
| `utils.py` | Starter helpers, including `chat_interface` |
