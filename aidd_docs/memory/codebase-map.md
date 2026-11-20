# Codebase Map
## Areas
- `aidd_docs/INSTALL.md` holds the target folder structure: one package per bounded context, each split into domain, application and infrastructure.
- `aidd_docs/memory/external/drlibre-specs.md` is the functional specification the code implements.
- `src/drlibre/shared_kernel/`: `Id`, `Clock` port, `Result`, `ErrorCode` (spec 4), `DomainError`, `UnitOfWork` port, `Page`/`PageRequest` (20 rows), `FieldErrors` and `Dependents` (`has_dependents` lists).
- `src/drlibre/audit/`: write side of the audit log; `AuditEntry` refuses personal metadata, `DjangoAuditLog` (append-only), `DjangoUnitOfWork` (`transaction.atomic`).
- `src/drlibre/identity/`: users, password sign-in, sessions (token hash), lockout (Redis), password change, user management, `authorize_owned` guard; `StaffLookup` inbound port for other contexts.
- `src/drlibre/organisation/`: hospitals, specialties, departments, rooms, appointment types, clinician profiles; `DjangoReferenceQueries` reads; `NoScheduleYet` null adapter until scheduling exists.
- `src/drlibre/health/`: health check context; `DatabaseProbe` port, PostgreSQL adapter, `SystemClock`.
- `src/drlibre/notifications/`: `Mailer` port and its SMTP adapter.
- `src/drlibre/interfaces/`: driving adapters; `api/` mounts Django Ninja at `/api/v1` (health, auth), `web/` holds views, presenters and templates (sign-in, role areas, admin console), `jobs/` holds Celery tasks.
- `src/drlibre/bootstrap/container.py`: the composition root; `use_container` swaps in fakes for tests.
- `config/`: settings from `.env` via pydantic-settings, urls, Celery app and beat schedule, correlation id middleware, structlog JSON logging.
- `tests/`: `features/` Gherkin (one file per Story), `use_cases/` pytest-bdd on fakes (`fakes/world.py` wires them), `contracts/` fake vs real, `presenters/` ViewModels, `api/` and `integration/` against compose services, `e2e/` Playwright journey with vendored axe-core.
- `docker/`, `docker-compose.yml`: image, entrypoint (migrate, seed, gunicorn) and the six-service stack.
- `.github/workflows/ci.yml`: CI, pre-commit gates and pytest against PostgreSQL, Redis and Mailpit services.
- `scripts/seed.py`: idempotent demo seed through the use cases (two hospitals, one sign-in per role), run with `python -m scripts.seed`.
- `static/vendor/`: vendored HTMX 2.0.11 and Pico.css 2.1.1; `static/drlibre.css` holds the few own rules.
