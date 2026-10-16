# External data: CultPass

Data from the CultPass platform, which UDA-Hub reads and acts on through the tools in `agentic/tools/cultpass_tools.py`.

| File | Contents |
|---|---|
| `cultpass.db` | The CultPass database, committed in its freshly seeded state. `01_external_db_setup.ipynb` rebuilds it from `data/models/cultpass.py`. |
| `cultpass_users.jsonl` | 6 customers (Alice Kingsley and David Noir are blocked) |
| `cultpass_experiences.jsonl` | 7 experiences across Brazil (4 of them premium) |
| `cultpass_articles.jsonl` | 18 knowledge base articles, loaded into `udahub.db` by notebook 02 |

**Tables in `cultpass.db`:**

- `users`
- `subscriptions`: status, tier and monthly quota
- `experiences`: date, slots and premium flag. Dates are set relative to when notebook 01 runs (1 to 7 days later).
- `reservations`

## Demo customers

These are the values in the committed `cultpass.db`:

| Customer | Id | Blocked | Subscription | Active reservations |
|---|---|---|---|---|
| Alice Kingsley | `a4ab87` | Yes | cancelled, premium, quota 8 | Modern Art at MASP, Pelourinho Colonial Walk |
| Bob Stone | `f556c0` | No | active, premium, quota 6 | Carnival History Tour in Olinda, Samba Night at Lapa |
| Cathy Bloom | `88382b` | No | active, basic, quota 4 | Sunset Paddleboarding |
| David Noir | `888fb2` | Yes | cancelled, basic, quota 3 | |
| Eva Green | `f1f10d` | No | cancelled, basic, quota 4 | |
| Frank Ocean | `e6376d` | No | active, premium, quota 2 | Pelourinho Colonial Walk |

Bob also has ticket history and a stored preference in `udahub.db`. The demo scenarios rely on these values. In
scenario 3, for example, Bob already has Samba Night booked.

## Resetting

The demos in notebook 03 make real changes: Cathy's reservation is cancelled, for example. Re-run notebook 01 to
reset the database. It pins the subscriptions and reservations of Bob, Cathy, Eva and Frank. Alice's and David's
subscriptions, Alice's reservations and the number of free slots are random, so they will differ from the table
above after a reset.
