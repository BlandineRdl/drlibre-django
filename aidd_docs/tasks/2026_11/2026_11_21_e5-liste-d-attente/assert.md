# Assert: E5 - Les créneaux libérés sont proposés aux patients en liste d'attente
## Round 1
- Head: `ac8ee90`
- Uncommitted changes: no
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `uv run pytest -m e2e` | not run | out of scope for phases 1-3 |
| `./scripts/load-run.sh` | not run | out of scope for phases 1-3 |

## Round 2
- Head: `1d048cb`
- Uncommitted changes: no
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `uv run pytest -m e2e` | not run | out of scope for phases 4-6 |
| `./scripts/load-run.sh` | not run | out of scope for phases 4-6 |

## Round 3
- Head: `aae6a96`
- Uncommitted changes: yes
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `uv run pytest -m e2e` | 0 | |
| `./scripts/load-run.sh` | not run | out of scope for phases 7-8: no search or booking query changed |
