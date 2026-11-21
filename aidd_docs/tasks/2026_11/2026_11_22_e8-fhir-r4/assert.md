# Assert: E8 - Un client FHIR R4 fait tout ce que les écrans permettent, ni plus ni moins
## Round 1
- Head: `7f0ebd4`
- Uncommitted changes: yes
- Verdict: FAIL

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pyrefly check` | 0 | |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | |
| `uv run pytest tests/fhir tests/use_cases/identity tests/contracts/test_api_tokens.py tests/contracts/test_readers.py tests/contracts/test_identity_repositories.py tests/api/test_same_origin.py tests/api/test_domain_errors.py tests/api/test_auth_endpoints.py tests/integration/test_seed.py` | 0 | |
| `uv run pytest tests/use_cases tests/contracts tests/api tests/presenters -q -p no:randomly` | 0 | |
| `uv run pytest tests/test_acceptance_names.py` | 1 | `Un client agit avec le jeton d'un utilisateur et exactement ses droits: bullets without a scenario` (5 bullets, phases 2 to 8) |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |
