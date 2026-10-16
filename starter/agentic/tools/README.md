# Tools

Each module provides plain Python functions, which hold the business rules and are unit-tested without an LLM.
The tools the agents call are thin LangChain wrappers around them.

## `cultpass_tools.py`: CultPass account tools

`build_account_tools(user_id, ticket_id)` returns the account agent's tools with the customer's id bound in, so the
LLM can never act on another customer's account. The tools are rebuilt on every turn.

| Tool | What it does | Rules enforced |
|---|---|---|
| `get_my_account` | Profile, blocked status, subscription, and quota used and remaining this month | |
| `get_my_reservations` | The customer's reservations: id, status, experience and date | |
| `find_experiences` | Upcoming experiences with free slots, by keyword and location | |
| `book_experience` | Reserves an experience | The id must have come from `find_experiences` or `get_my_reservations` in this turn. The account must not be blocked and the subscription must be active. Premium experiences need the premium tier. There must be free slots and quota left. No double booking. |
| `cancel_my_reservation` | Cancels a reservation and returns the credit if it's at least 24h before the event | The id must have come from `get_my_reservations` in this turn, or from a booking made in this turn. The reservation must belong to the customer and still be active. |
| `change_subscription` | Pauses, resumes or cancels the subscription | Only valid state changes are allowed. Blocked accounts can't make changes. |
| `request_refund` | Registers a refund request as a system message on the ticket and returns a reference such as `RF-1A2B3C` | It doesn't issue a refund. Its use always escalates the ticket (`ESCALATING_TOOLS`), because refunds need support-lead approval. |

An id that wasn't looked up gets an error telling the agent which lookup to call. The error is returned rather
than raised, so the agent can recover.

The underlying functions (`get_customer_profile`, `find_customer_by_email`, `list_reservations`,
`search_experiences`, `reserve_experience`, `cancel_reservation`, `manage_subscription`) are also used directly
by the supervisor and the memory nodes.

## `knowledge_tools.py`: RAG over the knowledge base

- **Retriever:** `KnowledgeRetriever` indexes the account's `knowledge` articles in an `InMemoryVectorStore` with OpenAI embeddings (`text-embedding-3-small`).
- **Search:** `search()` returns the top 3 articles scoring at least 0.30 cosine similarity.
- **Fallback:** if embeddings are unavailable, it falls back to IDF keyword scoring with light stemming, so the tests run offline.
- **Caching:** `get_retriever()` builds each account's index once.
- **Tool:** `search_knowledge_base` gives the account agent access to the same retriever.

## `ticket_tools.py`: tickets and long-term memory in `udahub.db`

| Function | What it does |
|---|---|
| `get_or_create_ticket` | Loads a ticket, or creates it with its user. Unknown customers get a per-account `guest` user. |
| `link_ticket_to_customer` | Moves a guest ticket to the identified customer |
| `add_message`, `get_ticket_messages` | The ticket's message log: user, AI and system messages, including handoff notes and refund requests |
| `update_ticket_metadata` | Status, main issue type, and tags (merged without duplicates) |
| `get_prior_tickets` | Summaries of the customer's previous tickets, recalled in new tickets |
| `get_memories`, `save_memory` | The `customer_memory` table. `save_memory` skips duplicates, ignoring case, punctuation and spacing. |

## `db.py`

Cached SQLAlchemy engines and a session context manager for `udahub.db` and `cultpass.db`. The paths come from
`agentic/config.py` and can be overridden with the `UDAHUB_DB_PATH` and `CULTPASS_DB_PATH` environment variables.
