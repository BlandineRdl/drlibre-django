---
status: done
---

# Instruction: Demo seed, end-to-end journey, docs
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── scripts/seed.py                        ✏️  seeders through use cases, idempotent on codes and emails
├── tests/
│   ├── integration/test_seed.py           ✅  run twice, same row counts
│   └── e2e/
│       ├── conftest.py                    ✅  base URL of the compose web service
│       ├── vendor/axe-4.14.1.min.js       ✅
│       └── test_admin_journey.py          ✅  marker e2e
├── README.md                              ✏️  demo sign-ins, e2e run
└── aidd_docs/memory/
    ├── codebase-map.md                    ✏️
    ├── coding-assertions.md               ✏️
    └── architecture.md                    ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d --build`, seed ran in the entrypoint | demo admin, clinician, patient exist | system |
| Happy path | demo admin chains hospital → department → room → type → clinician user → profile | each step listed in the console | browser |
| Happy path | admin deletes the new hospital | refusal lists its department | browser |
| Edge case | demo clinician opens `/console/` | forbidden page | browser |
| Edge case | anonymous opens `/console/` | redirected to sign-in | browser |
| Edge case | axe-core on sign-in, list, form, confirm pages at 375 and 1440 px | no WCAG 2.x A/AA violation, no horizontal scroll | browser |
| Edge case | seed run twice | no duplicate rows | system |
| Teardown | journey data uses unique codes per run | no clash on rerun | system |

## Tasks to do
### `1)` Demo seed
> One demo sign-in per role and a small multi-hospital referential.

1. Seeders for two hospitals with distinct time zones, departments, rooms, types, specialties, admin, clinician with profile, patient with password; get-or-create on code and email.

### `2)` End-to-end journey
> Prove the Epic's Success Evidence in a real browser.

1. `test_admin_journey.py`: the chain, refused delete, clinician 403, anonymous redirect, axe-core checks at both widths.
2. Run `uv run playwright install chromium` then `uv run pytest -m e2e` against the compose stack.

### `3)` Documentation
> Memory matches the code.

1. Update codebase map, coding assertions (e2e command), architecture (session cookie, origin check, null dependents adapters), README demo sign-ins.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `test_seed.py` green; `python -m scripts.seed` twice leaves counts unchanged |
| 2 | `pytest -m e2e` green against `localhost:8000` |
| 3 | docs name every new context and command; `pre-commit run --all-files` green |
