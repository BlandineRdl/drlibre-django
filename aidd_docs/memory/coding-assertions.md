# Coding Assertions
## Prerequisites
- Docker and uv must be installed before any gate can run.
- `cp .env.example .env` once, then set a real `SECRET_KEY`.

## Gates
- `uv run pre-commit run --all-files`: Ruff lint and format, Pyrefly, import-linter, Python Doctor (min score 90).
- `uv run lint-imports`: hexagon boundaries alone.
- `docker compose up -d` then `uv run pytest`: the full suite; `-m "not integration"` skips tests needing PostgreSQL or Mailpit.
- `curl -i localhost:8000/api/v1/health`: 200 with an `x-correlation-id` header.
