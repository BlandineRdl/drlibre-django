# Assert: E4 - Le patient gère ses rendez-vous et reste informé
## Round 1
- Head: `3bd3b62`
- Uncommitted changes: yes
- Verdict: FAIL

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 1 | `python-doctor ... Failed` (score 70: scans the foreign git worktree `.claude/worktrees/fervent-banach-a724ed`, its `.venv` included; a clean export of the index scores 90) |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run pytest -m e2e` | not run | phase 1 changes no page |

## Round 2
- Head: `e26e82f`
- Uncommitted changes: yes
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run pytest -m e2e` | not run | phase 2 changes no page |

## Round 3
- Head: `2d64f89`
- Uncommitted changes: yes
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run pytest -m e2e` | not run | phase 3 changes no page |

## Round 4
- Head: `31a5fc4`
- Uncommitted changes: yes
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run pytest -m e2e` | not run | phase 4 changes no page |

## Round 5
- Head: `5245f6d`
- Uncommitted changes: yes
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run pytest -m e2e` | not run | phase 5 changes no page |

## Round 6
- Head: `4ec2a4d`
- Uncommitted changes: yes
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run pytest -m e2e` | 0 | portal pages also checked with axe at 375 and 1440 px for the passwordless demo patient: no violation |

## Round 7
- Head: `6334f3b`
- Uncommitted changes: yes
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | 200 with `x-correlation-id` |
| `uv run pytest` | 0 | |
| `uv run pytest -m e2e` | 0 | |
