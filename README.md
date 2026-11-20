# DrLibre-django
Hospital appointment scheduling, a hexagonal Django back end. Portfolio sandbox, fictitious data, localhost only.

## Run
1. `cp .env.example .env` and set a real `SECRET_KEY`.
2. `docker compose up` starts web, worker, beat, PostgreSQL, Redis and Mailpit.
3. `curl -i localhost:8000/api/v1/health`; Mailpit inbox at `localhost:8025`.

## Develop
1. `uv sync` and `uv run pre-commit install`.
2. With the stack up: `uv run pytest`.
3. `uv run pre-commit run --all-files` runs every gate.

Design and stack: `aidd_docs/INSTALL.md`.
