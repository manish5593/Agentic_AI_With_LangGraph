All of your agents go in this folder

| Module | Agent |
|---|---|
| `classifier.py` | Classifier: structured ticket triage |
| `supervisor.py` | Supervisor: customer identification, routing rules, `request_info` |
| `knowledge_agent.py` | Knowledge resolver: RAG over the knowledge base |
| `account_agent.py` | Account resolver: ReAct agent with CultPass tools |
| `quality_gate.py` | Quality gate: resolve vs. escalate decision |
| `escalation_agent.py` | Escalation: human handoff note and customer reply |
| `memory_agent.py` | Memory: `load_context`, `finalize`, `write_memory` |
| `common.py` | Shared prompt-context and tracing helpers |
