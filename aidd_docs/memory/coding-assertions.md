# Coding Assertions
## Prerequisites
- Docker and uv must be installed before any gate can run.
- `cp .env.example .env` once, then set a real `SECRET_KEY`.

## Gates
- `uv run pre-commit run --all-files`: django-upgrade, Ruff lint and format, Pyrefly, import-linter, Python Doctor (min score 90, on the git index), `check --deploy` with `HTTPS_ONLY=true`, `makemigrations --check`.
- GitHub Actions `.github/workflows/ci.yml` runs pre-commit (Python Doctor included), the full suite and the HL7 FHIR validator on every pull request.
- `uv run lint-imports`: hexagon boundaries alone.
- `docker compose up -d` then `uv run pytest`: the full suite; `-m "not integration"` skips tests needing PostgreSQL or Mailpit.
- `curl -i localhost:8000/api/v1/health`: 200 with an `x-correlation-id` header.
- `curl -i localhost:8000/fhir/metadata`: 200 `CapabilityStatement` in `application/fhir+json` with an `x-correlation-id` header.
- `docker compose up -d --build`, `uv run playwright install chromium` once, then `uv run pytest -m e2e`: the Playwright journey against `localhost:8000`, axe-core at 375 and 1440 px; excluded from the default run and CI.
- `docker compose up -d --build` then `./scripts/fhir-validate.sh`: every `/fhir` answer on the demo seed (`scripts/fhir_samples.py`, each reader) passes the pinned HL7 validator 7.0.6 for R4 4.0.1 with zero error; needs Java 11+, the jar is cached in `.cache/`; CI job `fhir-conformance` runs it on the seeded app.
- `./scripts/load-run.sh`: Locust search and booking p95 on the load seed, in its own compose project removed at exit.
- pre-commit `--all-files` only lints tracked files: run `uv run ruff check .` and `uv run ruff format --check .` before new files are staged.
- Commit the whole index: `git commit -- <paths>` makes pre-commit stash the other staged work and check a mixed tree; never skip a failing hook, fix its cause.
