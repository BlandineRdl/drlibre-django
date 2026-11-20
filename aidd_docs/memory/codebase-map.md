# Codebase Map
## Areas
- `aidd_docs/INSTALL.md` holds the target folder structure: one package per bounded context, each split into domain, application and infrastructure.
- `aidd_docs/memory/external/drlibre-specs.md` is the functional specification the code implements.
- `src/drlibre/shared_kernel/`: `Id`, `Clock` port, `Result`, `ErrorCode` (spec 4) and `DomainError`.
- `src/drlibre/health/`: health check context; `DatabaseProbe` port, PostgreSQL adapter, `SystemClock`.
- `src/drlibre/notifications/`: `Mailer` port and its SMTP adapter.
- `src/drlibre/interfaces/`: driving adapters; `api/` mounts Django Ninja at `/api/v1`, `jobs/` holds Celery tasks.
- `src/drlibre/bootstrap/container.py`: the composition root; `use_container` swaps in fakes for tests.
- `config/`: settings from `.env` via pydantic-settings, urls, Celery app and beat schedule, correlation id middleware, structlog JSON logging.
- `tests/`: `features/` Gherkin, `use_cases/` pytest-bdd on fakes, `contracts/` fake vs real, `integration/` against compose services, `fakes/` in-memory adapters.
- `docker/`, `docker-compose.yml`: image, entrypoint (migrate, seed, gunicorn) and the six-service stack.
- `scripts/seed.py`: idempotent seed, run with `python -m scripts.seed`.
- `static/vendor/`: vendored HTMX 2.0.11.
