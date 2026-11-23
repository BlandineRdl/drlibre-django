# Assert: formulaires Django
## Round 1
- Head: `783c0f9`
- Uncommitted changes: yes
- Verdict: PASS

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pre-commit run --all-files` | 0 | |
| `uv run pytest` | 0 | |
| `curl -i localhost:8000/api/v1/health` | 0 | |
| `curl -i localhost:8000/fhir/metadata` | 0 | |
| `uv run pytest -m e2e` | not run | out of phase 1 scope |
| `./scripts/fhir-validate.sh` | not run | no FHIR change |
| `./scripts/load-run.sh` | not run | no performance change |
