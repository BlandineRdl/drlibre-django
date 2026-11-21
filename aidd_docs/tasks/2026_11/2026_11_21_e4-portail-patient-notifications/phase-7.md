---
status: done
---

# Instruction: Parcours end-to-end, documentation, gates
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── aidd_docs/
│   ├── backlog/open-questions.md                                ✏️  E4 answers, pointing to this plan
│   └── memory/{architecture.md,codebase-map.md,testing.md}      ✏️
└── tests/e2e/
    ├── pages.py                                                 ✏️  `read_mail(to, subject)` to tell the three emails apart
    └── test_patient_manages_appointments.py                     ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d --build`, demo seed, rate limits flushed | stack healthy | system |
| Happy path | visitor books for `visiteur@drlibre.localhost`, signs in by link, sees the appointment, reschedules, then cancels | each step: a notification in the portal and an email in Mailpit, neither with the reason or a name in the notification | browser |
| Edge case | every portal page at 375 and 1440 px | axe finds no WCAG 2.2 AA violation, no horizontal scroll | browser |
| Teardown | rate limits flushed | baseline | system |

## Tasks to do
### `1)` End-to-end journey
> Epic Success Evidence in the browser.

1. Playwright journey per Test Scope, `check_accessible` on each portal page.

### `2)` Documentation
> Memory matches the code.

1. `architecture.md`: in-app notifications, reminder beat entry, exclusion and check constraints, reschedule ignoring its appointment, `CONFIRMED` removed.
2. `codebase-map.md`: notifications and portal; `open-questions.md`: E4 answers; `testing.md` only if a layer changed.

### `3)` Gates
> Contributor checks before the pull request.

1. `uv run ruff check .`, `uv run ruff format --check .`, `uv run pre-commit run --all-files`, `uv run lint-imports`.
2. `docker compose up -d`, `uv run pytest`; `uv run pytest -m e2e`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | e2e green; Mailpit holds booking, reschedule and cancellation emails without the reason |
| 2 | each doc names the new parts it lists |
| 3 | every gate passes |
