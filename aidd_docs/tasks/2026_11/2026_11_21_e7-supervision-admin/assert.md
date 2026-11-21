# Assert: E7 - L'admin supervise l'activité de tous les hôpitaux
## Round 1
- Head: `0e2e3cb`
- Uncommitted changes: yes
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pytest` | 0 | |
| `uv run pytest -m e2e` | 0 | |
