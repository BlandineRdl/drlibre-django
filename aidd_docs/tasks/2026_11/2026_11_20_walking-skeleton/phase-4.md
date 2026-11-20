---
status: pending
---

# Instruction: Compose stack, Celery, seed, Mailpit
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── docker/Dockerfile                    ✅  uv-based, python 3.13-slim
├── docker/entrypoint.sh                 ✅  migrate + seed for web
├── docker-compose.yml                   ✅  web, worker, beat, postgres:17, redis:8, mailpit
├── .env.example                         ✅
├── .dockerignore                        ✅
├── config/celery.py                     ✅  app + beat_schedule
├── config/__init__.py                   ✅  load celery app
├── scripts/seed.py                      ✅  idempotent, empty seeder list
├── static/vendor/htmx-2.0.x.min.js      ✅  pinned HTMX
├── src/drlibre/interfaces/jobs/tasks.py ✅  heartbeat task
├── src/drlibre/notifications/
│   ├── application/ports/outbound.py    ✅  Mailer Protocol + EmailMessage
│   └── infrastructure/smtp_mailer.py    ✅  Django mail backend adapter
├── src/drlibre/bootstrap/container.py   ✅  mailer wiring
└── tests/
    ├── fakes/in_memory_mailer.py        ✅
    ├── contracts/test_mailer.py         ✅  fake and SMTP
    ├── integration/test_mailpit.py      ✅  send then read Mailpit API
    └── use_cases/test_heartbeat.py      ✅  task runs eagerly on fakes
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `cp .env.example .env` | stack configured | cli |
| Happy path | `docker compose up -d` | 6 services running, web and postgres healthy | cli |
| Happy path | `curl -i localhost:8000/api/v1/health` | 200 with `x-correlation-id` | api |
| Happy path | open `localhost:8025` | Mailpit UI answers 200 | browser |
| Happy path | wait one beat period | worker logs JSON `heartbeat` with health status | system |
| Edge case | run seed twice | second run changes nothing, exit 0 | cli |
| Teardown | `docker compose down -v` | baseline restored | cli |

## Tasks to do
### `1)` Image and compose
> One command starts the stack.

1. Dockerfile with uv, non-root user, `uv sync --frozen --no-dev`.
2. Compose: `web` (gunicorn on 8000), `worker` (`celery -A config worker`), `beat` (`celery -A config beat`), `postgres:17` with healthcheck, `redis:8`, `axllent/mailpit` (1025, 8025); web, worker, beat depend on healthy postgres and redis.
3. `.env.example` with every Settings field; host ports for postgres and redis exposed for integration tests.

### `2)` Celery and beat
> Worker and beat wired, dummy task scheduled.

1. `config/celery.py`: app from settings, broker `REDIS_URL`, `beat_schedule` running `heartbeat` every 60 s.
2. `heartbeat` resolves `CheckHealth` from the container and logs its report.

### `3)` Mailer port
> Mail sending behind a port, for Mailpit proof.

1. `Mailer` Protocol `send(message: EmailMessage) -> None`; `SmtpMailer(Mailer)` via Django SMTP backend to `EMAIL_HOST:EMAIL_PORT`.
2. `InMemoryMailer(Mailer)` fake keeps `sent` list.
3. Contract suite over both; integration test queries Mailpit `GET /api/v1/messages` and finds the subject.

### `4)` Seed and HTMX
> Extension points.

1. `scripts/seed.py` sets up Django, runs `SEEDERS: list[Callable[[], None]] = []` in one transaction, logs count.
2. Vendor HTMX 2.0.x minified file; `STATICFILES_DIRS` points to `static/`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `docker compose ps` lists 6 running services |
| 2 | worker log shows a `heartbeat` JSON line within 90 s |
| 3 | Mailpit receives the test message |
| 4 | seed runs twice with exit 0; HTMX file version starts with `2.0.` |
