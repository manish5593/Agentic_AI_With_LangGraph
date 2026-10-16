# External data: CultPass

Data from the CultPass platform, which UDA-Hub reads and acts on through the tools in `agentic/tools/cultpass_tools.py`.

| File | Contents |
|---|---|
| `cultpass.db` | CultPass database, built by `01_external_db_setup.ipynb` from `data/models/cultpass.py` |
| `cultpass_users.jsonl` | 6 customers (Alice Kingsley and David Noir are blocked) |
| `cultpass_experiences.jsonl` | 7 experiences across Brazil (every other one is premium) |
| `cultpass_articles.jsonl` | 18 knowledge base articles, loaded into `udahub.db` by notebook 02 |

**Tables in `cultpass.db`:** `users`, `subscriptions` (status, tier, monthly quota), `experiences` (date, slots,
premium flag) and `reservations`.

**Demo customers** (notebook 01 sets these values so the demos are repeatable):

| Customer | Id | Subscription | Notes |
|---|---|---|---|
| Alice Kingsley | `a4ab87` | random | Blocked; has 2 reservations |
| Bob Stone | `f556c0` | active, premium, quota 6 | 2 reservations; has ticket history and a stored preference in `udahub.db` |
| Cathy Bloom | `88382b` | active, basic, quota 4 | 1 reservation |
| David Noir | `888fb2` | random | Blocked |
| Eva Green | `f1f10d` | cancelled, basic | |
| Frank Ocean | `e6376d` | active, premium, quota 2 | 1 reservation |

Re-run notebook 01 to reset the database after the demos, which make real bookings and cancellations.
