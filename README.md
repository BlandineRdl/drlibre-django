# DrLibre-django
Hospital appointment scheduling, a hexagonal Django back end. Portfolio sandbox, fictitious data, localhost only.

## Run
1. `cp .env.example .env` and set a real `SECRET_KEY`.
2. `docker compose up` starts web, worker, beat, PostgreSQL, Redis and Mailpit.
3. `curl -i localhost:8000/api/v1/health`; Mailpit inbox at `localhost:8025`.
4. Sign in at `localhost:8000/sign-in` with a demo account (fictitious, localhost only), password `drlibre-demo-2026`:
   - admin: `admin@drlibre.localhost`
   - clinician: `clinicien@drlibre.localhost`
   - second clinician, same department: `clinicien2@drlibre.localhost`
   - patient: `patient@drlibre.localhost`
   - passwordless patient, signs in by email link only: `visiteur@drlibre.localhost`
5. Both demo clinicians work Monday to Friday, 09:00–12:00 and 14:00–17:00 (Paris): edit at `/workspace/availability/` and `/workspace/time-off/`; signed in, `GET /api/v1/slots?type=…&clinician=…&start=…&end=…` lists free slots.

## Develop
1. `uv sync` and `uv run pre-commit install`.
2. With the stack up: `uv run pytest`.
3. `uv run pre-commit run --all-files` runs every gate.
4. End-to-end: `uv run playwright install chromium` once, `docker compose up -d --build`, then `uv run pytest -m e2e`.

Design and stack: `aidd_docs/INSTALL.md`.
