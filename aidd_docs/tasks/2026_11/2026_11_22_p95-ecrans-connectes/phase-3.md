---
status: done
---

# Instruction: Run, record p95, file fix issues
## Architecture projection
```txt
.
└── aidd_docs/
    ├── memory/
    │   ├── codebase-map.md ✏️
    │   └── testing.md ✏️
    └── tasks/
        └── 2026_11/
            └── 2026_11_22_p95-ecrans-connectes/
                └── load-results.md ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | Demo stack untouched | `drlibre-load` project only | cli |
| Happy path | `./scripts/load-run.sh` | p95 per endpoint for every role | cli |
| Edge case | A p95 >= 200 ms | Its slow SQL explained and a GitHub issue filed | cli |
| Teardown | Script exit | Load stack and volume removed | cli |

## Tasks to do
### `1)` Run
1. `./scripts/load-run.sh` (2 min, `-u 20`); raise `-u`/`-t` only if an endpoint gets < 50 successes; keep the exact command.

### `2)` Record
1. Write `load-results.md` in E3's format: setup (machine, volumes incl. audit and notifications), command, p95 table per role, failures by code, verdict.

### `3)` Fix issues
1. For each p95 >= 200 ms: find the slow SQL (`EXPLAIN ANALYZE` on the stack kept with `--keep`), `gh issue create` with endpoint, p95, plan and proposed index or query change; link it in `load-results.md`.

### `4)` Docs and gates
1. Update the `codebase-map.md` loadtests line and the `testing.md` performance row to name the signed-in scenarios.
2. Run `uv run pre-commit run --all-files` and `uv run pytest -m "not e2e"`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | Every endpoint of #23 has >= 50 successes |
| 2 | `load-results.md` lists a p95 per endpoint of #23 |
| 3 | Each p95 >= 200 ms links an open issue |
| 4 | Gates pass |
