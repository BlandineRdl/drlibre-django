---
status: done
---

# Instruction: Seed, parcours end-to-end, documentation, gates
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── scripts/seed.py                                              ✏️  idempotent demo appointments for the demo clinician through the use cases
├── tests/e2e/test_clinician_runs_the_day.py                     ✅  Success Evidence journey + axe 375 and 1440 px
└── aidd_docs/
    ├── memory/architecture.md                                   ✏️
    ├── memory/codebase-map.md                                   ✏️
    └── backlog/open-questions.md                                ✏️  E6 answers
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d --build`, seed run twice | same rows, no duplicate | cli |
| Happy path | demo clinician: `BOOKED` → `CHECKED_IN` → `COMPLETED`, another `NO_SHOW`, a third cancelled with reason | statuses shown; Mailpit receives « RDV annulé » for the patient; patient portal shows the notification | browser |
| Edge case | forbidden transition through the API; other clinician's appointment page | `invalid_transition` with `status`; « Not your appointment » | browser |
| Edge case | notes saved | absent from audit metadata and from the patient portal | browser |
| Happy path | every workspace page | axe clean at 375 and 1440 px, no horizontal scroll | browser |
| Teardown | e2e cleans its appointments, `clear_mail`, `reset_rate_limits` | baseline | browser |

## Tasks to do
### `1)` Demo data
> The Success Evidence needs today's appointments.

1. `seed_demo_appointments`: a few `BOOKED` appointments of the passwordless patient with the demo clinician on the next working day slots, via `BookForPatient`, skipped when present.

### `2)` End-to-end journey
> Success Evidence of the Epic.

1. `test_clinician_runs_the_day.py` books its own appointments through the API, then drives the workspace.

### `3)` Documentation
> Memory matches the code.

1. Update `architecture.md`, `codebase-map.md`, record E6 answers in `open-questions.md` from the plan's decisions.

### `4)` Gates
> Contributor checks from `aidd_docs/memory/coding-assertions.md`.

1. `uv run ruff check .`, `uv run ruff format --check .`, `uv run pre-commit run --all-files`, `uv run lint-imports`.
2. `docker compose up -d` then `uv run pytest`; `uv run pytest -m e2e`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | seed idempotent; demo clinician sees appointments on the seeded day |
| 2 | every Success Evidence bullet observed in the browser |
| 3 | docs name the new ports, screens and decisions |
| 4 | all gates green, Python Doctor ≥ 90 |
