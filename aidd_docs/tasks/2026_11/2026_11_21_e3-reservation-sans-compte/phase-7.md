---
status: done
---

# Instruction: Seed de charge, Locust, parcours end-to-end, documentation
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── pyproject.toml                                         ✏️  dev dependency `locust`
├── scripts/seed.py                                        ✏️  demo: online types, a passwordless demo patient; `--size load`: 10 hospitals, 200 clinicians, 5k patients, 50k appointments, idempotent
├── loadtests/locustfile.py                                ✅  search (three lists, filters) and booking (hold, code from Mailpit, verify; signed-in `POST /appointments`)
├── tests/e2e/
│   ├── pages.py                                           ✏️  `read_code(mailpit)`, `read_link(mailpit)`, `reset_rate_limits()` flushing `drlibre:rate:*` in compose Redis
│   ├── test_visitor_books_without_account.py              ✅  search → slot → details → code → confirmation → portal; axe at 375 and 1440 px
│   └── test_patient_signs_in_by_link.py                   ✅  link request → Mailpit → Continuer → portal; axe
└── aidd_docs/
    ├── memory/architecture.md                             ✏️  booking and search contexts, hold read-time filter, null adapters replaced, network limit setting
    ├── memory/codebase-map.md                             ✏️  booking, search, loadtests
    ├── memory/testing.md                                  ✏️  search scenarios on PostgreSQL; Locust run command
    ├── backlog/open-questions.md                          ✏️  E3 answers pointing to this plan's Decisions
    └── tasks/2026_11/2026_11_21_e3-reservation-sans-compte/load-results.md ✅  p95 per endpoint, machine stated
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d --build`; `python -m scripts.seed --size load`; `NETWORK_HOURLY_LIMIT` raised for the run | load data present, seed rerun adds nothing | cli |
| Happy path | Playwright journeys | both pass, axe clean at 375 and 1440 px | browser |
| Happy path | `locust -f loadtests/locustfile.py --headless -u 20 -r 5 -t 2m --host http://localhost:8000` | search and booking p95 < 200 ms | cli |
| Edge case | seed run twice | same row counts | cli |
| Teardown | `docker compose down -v` optional; limit setting restored | baseline | cli |

## Tasks to do
### `1)` Seed and load
> Prove p95 on realistic volume.

1. Seed `--size load` via the use cases or bulk inserts with slot refresh; idempotent.
2. Locustfile; run; record results; tune indexes from `EXPLAIN ANALYZE` if p95 fails.

### `2)` End-to-end
> Success Evidence of the Epic, in the browser.

1. Two Playwright journeys with axe.
2. Read `docker compose logs worker web` after the journeys: no code, no link token.

### `3)` Docs and contributor checks
> Memory matches the code.

1. Update the memory files and open questions.
2. Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run pre-commit run --all-files`, `uv run lint-imports`, `uv run pytest`, `uv run pytest -m e2e` (coding-assertions.md).

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `load-results.md` shows p95 < 200 ms for search and booking on the load seed |
| 2 | `uv run pytest -m e2e` green |
| 3 | every gate of coding-assertions.md green |
