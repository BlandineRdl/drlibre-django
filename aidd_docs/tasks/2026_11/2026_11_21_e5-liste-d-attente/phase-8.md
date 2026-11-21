---
status: pending
---

# Instruction: Parcours end-to-end, documentation, gates
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── aidd_docs/
│   ├── backlog/open-questions.md                                ✏️  E5 answers, pointing to this plan
│   └── memory/{architecture.md,codebase-map.md}                 ✏️
└── tests/e2e/
    └── test_waitlist_offer_journey.py                           ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d --build`, demo seed, rate limits and mail flushed | stack healthy | system |
| Happy path | `visiteur@drlibre.localhost` signs in by link and joins for the demo type; `patient@drlibre.localhost` books a slot more than 24 h ahead in that window and cancels it; the first sees « Créneau proposé » in-app and in Mailpit, accepts | RDV `BOOKED` in « Mes RDV »; « Créneau réservé » in-app and in Mailpit; no reason in either | browser |
| Edge case | portal and console waitlist pages at 375 and 1440 px | axe finds no WCAG 2.2 AA violation, no horizontal scroll | browser |
| Teardown | rate limits flushed | baseline | system |

## Tasks to do
### `1)` End-to-end journey
> Epic Success Evidence in the browser.

1. Playwright journey per Test Scope with `read_mail(to, subject)` and `check_accessible`; admin console waitlist page checked for accessibility.

### `2)` Documentation
> Memory matches the code.

1. `architecture.md`: waitlist in booking, lock order with waitlist entries, offer in the cancel transaction, expiry beat, optional notification appointment, partial unique offer index.
2. `codebase-map.md`: booking waitlist, `SqlWaitlistQueries`, portal and console waitlist pages, API routes.
3. `open-questions.md`: each E5 question answered from plan Decisions.

### `3)` Gates
> Contributor checks from `aidd_docs/memory/coding-assertions.md`.

1. `uv run ruff check .`, `uv run ruff format --check .`, `uv run pre-commit run --all-files`, `uv run lint-imports`, `uv run pytest`, `uv run pytest -m e2e`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | journey green; Mailpit holds both emails without the reason |
| 2 | docs read back against the code |
| 3 | every command exits 0 |
