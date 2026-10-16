# Core database (`udahub.db`)

UDA-Hub's own database, built by `02_core_db_setup.ipynb` from the models in `data/models/udahub.py`.

| Table | Contents |
|---|---|
| `accounts` | Platforms served by UDA-Hub (currently `cultpass`) |
| `users` | UDA-Hub users, linked to each platform's own user id through `external_user_id`. Unidentified customers use a per-account `guest` user. |
| `tickets` | Support tickets. The ticket id is also the LangGraph `thread_id`. |
| `ticket_metadata` | Status (`open`, `awaiting_customer`, `resolved`, `escalated`), main issue type and tags |
| `ticket_messages` | Full message log: `user`, `ai` and `system` messages, including escalation handoff notes and refund requests |
| `knowledge` | Knowledge base articles per account (18 for CultPass), used for RAG |
| `customer_memory` | Long-term memory: preferences and facts about a customer, recalled in every new ticket |

**Demo data:** the CultPass account, 18 articles, Alice's open login ticket, and a resolved past login ticket
(`past-bob-login`) plus a stored preference for Bob Stone.

Re-run notebook 02 to reset the database. This also deletes any tickets and memories the agents created.
