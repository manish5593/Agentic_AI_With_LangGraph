# Core database (`udahub.db`)

UDA-Hub's own database. It is committed in its freshly seeded state, and `02_core_db_setup.ipynb` rebuilds it from
the models in `data/models/udahub.py`.

| Table | Contents |
|---|---|
| `accounts` | Platforms served by UDA-Hub (currently `cultpass`) |
| `users` | UDA-Hub users, linked to each platform's own user id through `external_user_id`. Unidentified customers use a per-account `guest` user. |
| `tickets` | Support tickets. The ticket id is also the LangGraph `thread_id`. |
| `ticket_metadata` | Status (`open`, `awaiting_customer`, `resolved`, `escalated`), main issue type and tags |
| `ticket_messages` | Full message log: `user`, `ai` and `system` messages, including escalation handoff notes and refund requests |
| `knowledge` | Knowledge base articles per account (18 for CultPass), used for RAG |
| `customer_memory` | Long-term memory: preferences, personal facts and reported issues, recalled in every new ticket for that customer |

## What's in the committed database

| Table | Rows | Contents |
|---|---|---|
| `accounts` | 1 | CultPass |
| `knowledge` | 18 | Articles from `data/external/cultpass_articles.jsonl` |
| `users` | 2 | Alice Kingsley and Bob Stone |
| `tickets` | 2 | Alice's open login ticket, and Bob's resolved past login ticket (`past-bob-login`) |
| `ticket_messages` | 3 | Alice's message, and Bob's message with the reply he got |
| `customer_memory` | 1 | Bob: "Enjoys music and dance experiences, especially in Rio de Janeiro" |

Bob's past ticket and preference let the demos show long-term memory. In scenario 7, for example, he gets
recommendations that match his preference.

## How the agents write to it

- Each new ticket id creates a ticket, along with a `guest` user if the customer is unknown. A guest ticket is moved to the real customer once they are identified.
- Every customer message and reply is logged. Escalations add a handoff note, and refund requests add a system message.
- Memories are only stored for identified customers, as third-person summaries. Reservation state, one-off requests and duplicates are filtered out (see [`agentic/agents/README.md`](../../agentic/agents/README.md)).

Re-run notebook 02 to reset the database. This deletes any tickets and memories the agents created.
