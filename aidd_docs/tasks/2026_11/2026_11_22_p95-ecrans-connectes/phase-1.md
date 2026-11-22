---
status: done
---

# Instruction: Load seed signs in and fills audit and notifications
## Architecture projection
```txt
.
├── scripts/
│   └── seed.py ✏️
└── tests/
    └── integration/
        └── test_seed.py ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | Empty test database | Ready | system |
| Happy path | `seed.main(size="load")` | Load clinicians sign in with `DEMO_PASSWORD`; one audit entry per load appointment; one notification per future BOOKED load appointment | system |
| Edge case | `seed.main(size="load")` twice | No duplicate audit entry or notification | system |
| Teardown | pytest-django rollback | Baseline restored | system |

## Tasks to do
### `1)` Password for load clinicians
> Load clinicians can sign in by password.

1. In `seed_load`, hash `DEMO_PASSWORD` once with the project's hasher and set it as `password_hash` on each load clinician `UserRecord`.

### `2)` Audit entries for load appointments
> The journal holds a realistic volume.

1. After the appointments `bulk_create`, bulk insert one `AuditEntryRecord` per load appointment: action `booking.appointment_booked`, entity `appointment`, `at` spread over the past 35 days, metadata without personal data, actor null.

### `3)` Notifications for load patients
> The notifications page holds a realistic volume.

1. Bulk insert one `NotificationRecord` per future BOOKED load appointment, kind, title and required `body` as booking's « RDV réservé » notice, zone `Europe/Paris`.

### `4)` Tests
1. Extend the load seed integration test (acceptance-style name) asserting a load clinician signs in, audit and notification counts, and idempotence.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | Signing in `load-clinician-000@drlibre.localhost` with `DEMO_PASSWORD` succeeds |
| 2 | Audit entries count equals load appointments count |
| 3 | Notifications count equals future BOOKED load appointments count |
| 4 | `uv run pytest tests/integration/test_seed.py` passes |
