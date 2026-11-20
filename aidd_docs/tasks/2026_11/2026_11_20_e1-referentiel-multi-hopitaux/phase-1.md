---
status: done
---

# Instruction: Audit, unit of work and web shell
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── pyproject.toml                         ✏️  argon2-cffi, redis, pytest-playwright (dev); import-linter containers
├── config/
│   ├── settings.py                        ✏️  apps, templates, PASSWORD_HASHERS, session cookie settings
│   ├── urls.py                            ✏️  mount web urls
│   └── middleware.py                      ✏️  SameOriginMiddleware
├── src/drlibre/
│   ├── shared_kernel/
│   │   ├── unit_of_work.py                ✅  UnitOfWork Protocol (context manager)
│   │   └── pagination.py                  ✅  Page[T], PageRequest (20 rows, fallback to page 1)
│   ├── audit/
│   │   ├── domain/audit_entry.py          ✅  AuditEntry value object, metadata guard (ids, counts, field names)
│   │   ├── application/ports/outbound.py  ✅  AuditLog Protocol
│   │   └── infrastructure/
│   │       ├── django/{apps,models}.py    ✅  AuditEntryRecord, append-only
│   │       ├── django/migrations/0001_initial.py ✅
│   │       ├── audit_log.py               ✅  DjangoAuditLog
│   │       └── unit_of_work.py            ✅  DjangoUnitOfWork (transaction.atomic)
│   ├── interfaces/web/
│   │   ├── urls.py                        ✅
│   │   ├── templates/base.html            ✅  Pico, skip link, landmarks, time zone slot
│   │   └── templates/errors/{403,404}.html ✅
│   └── bootstrap/container.py             ✏️  audit_log, unit_of_work
├── static/vendor/pico-2.1.1.min.css       ✅
└── tests/
    ├── conftest.py                        ✏️  fake container gains fakes
    ├── fakes/{audit_log,unit_of_work}.py  ✅  InMemoryAuditLog (can fail), InMemoryUnitOfWork
    ├── contracts/test_audit_log.py        ✅
    ├── integration/test_unit_of_work_postgres.py ✅  audit failure rolls back the write
    └── api/test_same_origin.py            ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d postgres redis mailpit`, `uv run pytest` | existing suite green before changes | system |
| Happy path | record an audit entry inside a unit of work | entry stored with actor, action, entity, correlation id | system |
| Edge case | audit log raises inside the unit of work | the write in the same unit is rolled back | system |
| Edge case | metadata carries an email or a free-text value | `AuditEntry` refuses it | system |
| Edge case | POST with `Origin: https://evil.example` | 403 `forbidden` | api |
| Teardown | test database flushed by pytest-django | baseline restored | system |

## Tasks to do
### `1)` Dependencies and settings
> Prepare the project for models, templates and password hashing.

1. Add `argon2-cffi>=25.1,<26`, `redis>=8.1,<9`; dev `pytest-playwright>=0.10,<0.11`; `uv lock`.
2. Add audit app, `TEMPLATES` (app dirs), `PASSWORD_HASHERS` (Argon2 first), `SESSION_COOKIE_NAME`-style constants for the own cookie.
3. Register pytest marker `e2e`, `addopts` excludes it.

### `2)` Audit context and unit of work
> Every write and its audit entry share one transaction.

1. `AuditEntry` with `from_event` constructor rejecting metadata values that are not ids, ints, status values or field-name tuples.
2. `AuditLog` port, `DjangoAuditLog` adapter, append-only model, migration.
3. `UnitOfWork` port, `DjangoUnitOfWork`, fakes, contract and integration tests.

### `3)` Same-origin guard
> Refuse cross-origin state changes, including anonymous API POSTs.

1. `SameOriginMiddleware` after `CorrelationIdMiddleware`; 403 JSON `forbidden` for `/api/`, 403 page otherwise.

### `4)` Web shell
> A base layout every screen extends.

1. Vendor Pico 2.1.1, `base.html` with skip link, `<main>`, nav slot, `lang="fr"`, 403 and 404 templates and handlers.
2. Pagination value objects in the shared kernel.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `uv sync --locked` and `manage.py check --deploy` pass |
| 2 | contract suite green on fake and PostgreSQL; failing audit rolls back the write |
| 3 | cross-origin POST → 403; same-origin and no-Origin POST pass through |
| 4 | `/does-not-exist` renders the 404 page with the base layout |
