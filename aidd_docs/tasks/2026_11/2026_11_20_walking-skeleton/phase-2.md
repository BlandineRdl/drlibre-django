---
status: pending
---

# Instruction: Health slice through the hexagon
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
src/drlibre/
├── shared_kernel/
│   ├── __init__.py              ✅
│   ├── ids.py                   ✅  Id value object (UUID)
│   ├── clock.py                 ✅  Clock Protocol
│   ├── result.py                ✅  Ok / Err
│   └── errors.py                ✅  ErrorCode enum + typed errors with HTTP status (spec 4)
├── health/
│   ├── domain/health_report.py  ✅  HealthReport (pure)
│   ├── application/
│   │   ├── ports/inbound.py     ✅  CheckHealth Protocol
│   │   ├── ports/outbound.py    ✅  DatabaseProbe Protocol
│   │   └── use_cases/check_health.py ✅
│   └── infrastructure/
│       ├── system_clock.py      ✅
│       └── database_probe.py    ✅  Django connection SELECT 1
├── interfaces/api/
│   ├── __init__.py              ✅  NinjaAPI /api/v1, error handler mapping ErrorCode → status
│   └── health.py                ✅  GET /health router
└── bootstrap/container.py       ✅  composition root
tests/
├── fakes/                       ✅  FixedClock, InMemoryDatabaseProbe
├── features/health.feature      ✅
├── use_cases/test_health.py     ✅  pytest-bdd steps on fakes
├── contracts/test_database_probe.py ✅  same suite, fake and real
└── integration/test_database_probe_postgres.py ✅
config/urls.py                   ✅  mount api
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | wire fakes in the container | use case built without Django | system |
| Happy path | `GET /api/v1/health` with DB up | 200 `{"status":"ok","database":"up","checked_at":...}` | api |
| Edge case | probe reports down | 503 with status `degraded` | api |
| Teardown | none | none | system |

## Tasks to do
### `1)` Shared kernel
> Primitives every context reuses.

1. `Id`, `Clock` Protocol, `Result` (`Ok`/`Err`), `ErrorCode` with the ten spec 4 codes and their HTTP status, `DomainError` carrying code and details.

### `2)` Health use case and ports
> A use case reading time and DB state only through ports.

1. `HealthReport(status, database, checked_at)` in domain.
2. `CheckHealth` inbound Protocol; `DatabaseProbe` outbound Protocol (`is_up() -> bool`).
3. `CheckHealthUseCase(CheckHealth)` takes `Clock` and `DatabaseProbe`.

### `3)` Adapters and wiring
> Real adapters plus one composition root.

1. `SystemClock(Clock)`, `DjangoDatabaseProbe(DatabaseProbe)` using `connection.cursor()`.
2. `bootstrap/container.py` builds use cases; the router gets `CheckHealth` from it only.
3. Ninja API at `/api/v1/`, `GET /health`, global handler turning `DomainError` into `{code, message, details}` with its status.

### `4)` Tests per level
> Prove the wiring.

1. Gherkin `health.feature` + pytest-bdd steps on `FixedClock` and `InMemoryDatabaseProbe`.
2. Contract suite parametrised over fake and `DjangoDatabaseProbe` (real one marked `integration`, `django_db`).
3. Integration test on PostgreSQL: probe up returns true.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `ErrorCode.CONFLICT.http_status == 409` etc. for all ten |
| 2 | BDD scenario passes with no Django import in `health/domain` or `health/application` |
| 3 | `curl localhost:8000/api/v1/health` returns 200 JSON |
| 4 | `uv run pytest` green, including `-m integration` with compose postgres up |
