---
status: pending
---

# Instruction: Persistance PostgreSQL, limites Redis, emails et expiration Celery, null adapters remplacés
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── config/
│   ├── settings.py                                        ✏️  booking app; `public_base_url`, `network_hourly_limit`
│   └── celery.py                                          ✏️  beat `expire-booking-holds` every 60 s
├── .env.example                                           ✏️  PUBLIC_BASE_URL, NETWORK_HOURLY_LIMIT
├── src/drlibre/booking/infrastructure/
│   ├── __init__.py                                        ✅
│   ├── django/{__init__,apps,models}.py                   ✅  AppointmentRecord, BookingHoldRecord (index clinician+start, expires_at; email), VerificationCodeRecord
│   ├── django/migrations/0001_initial.py                  ✅
│   ├── repositories.py                                    ✅  DjangoAppointments, DjangoHolds, DjangoVerificationCodes
│   ├── queries.py                                         ✅  DjangoBookingQueries: active appointments of a clinician, open holds, dependents, upcoming of a user
│   ├── code_issuer.py                                     ✅  `secrets` 6 digits, HMAC-SHA256 with SECRET_KEY
│   ├── directory.py                                       ✅  OrganisationBookingDirectory over organisation ReferenceQueries and identity StaffLookup
│   ├── round_robin_ledger.py                              ✅  over organisation RecordRoundRobinAssignment
│   ├── free_slots.py                                      ✅  SchedulingFreeSlots over scheduling FindFreeSlots
│   ├── slot_refresh.py                                    ✅  SchedulingSlotRefresh over scheduling RefreshSlots
│   ├── schedule_locks.py                                  ✅  clinician profile and patient row `select_for_update`
│   └── patients.py                                        ✅  IdentityPatients over identity inbound ports
├── src/drlibre/identity/
│   ├── infrastructure/django/models.py                    ✏️  phone, birth_date, email_verified_at
│   ├── infrastructure/django/migrations/0002_patient_details.py ✅
│   ├── infrastructure/repositories.py                     ✏️  new user fields
│   ├── infrastructure/rate_limiter.py                     ✅  RedisRateLimiter (sorted set per hashed key, TTL)
│   └── infrastructure/upcoming_appointments.py            ✏️  BookingUpcomingAppointments replaces NoAppointmentsYet
├── src/drlibre/scheduling/
│   ├── application/ports/outbound.py                      ✏️  `SlotHolds.open(clinician_ids, within, at, ignoring)`
│   ├── application/ports/inbound.py                       ✏️  SlotAvailability (is_free, free_clinicians)
│   ├── application/use_cases/find_free_slots.py           ✏️  drops slots overlapping open holds (+ buffer of the type), then dedups by start
│   ├── application/use_cases/slot_availability.py         ✅
│   ├── infrastructure/slot_queries.py                     ✏️  returns clinician with each slot, no `distinct`
│   ├── infrastructure/no_appointments_yet.py              ❌  replaced by booking_appointments.py
│   ├── infrastructure/booking_appointments.py             ✅  ClinicianAppointments over booking queries
│   └── infrastructure/booking_holds.py                    ✅  SlotHolds over booking OpenHolds
├── src/drlibre/organisation/infrastructure/schedule_dependents.py ✏️  appointment dependents for types and profiles from booking
├── src/drlibre/organisation/application/ports/inbound.py  ✏️  RecordRoundRobinAssignment
├── src/drlibre/organisation/application/use_cases/record_round_robin_assignment.py ✅
├── src/drlibre/notifications/infrastructure/celery_outbox.py ✅  CeleryEmailOutbox: on_commit → send_task("drlibre.send_email")
├── src/drlibre/interfaces/jobs/tasks.py                   ✏️  `drlibre.send_email` (autoretry, backoff, 5 retries), `drlibre.expire_booking_holds`
├── src/drlibre/bootstrap/container.py                     ✏️  real adapters
├── src/drlibre/audit/domain/audit_entry.py                ✏️  only if a new text key is needed (expected none)
└── tests/
    ├── contracts/test_booking_repositories.py             ✅  fake vs Django: appointments, holds, codes, open holds after expiry
    ├── contracts/test_rate_limiter.py                     ✅  fake vs Redis
    ├── contracts/test_free_slots_with_holds.py            ✅  fake vs real slot query with open and expired holds
    ├── integration/test_booking_postgres.py               ✅  verify books, refreshes `scheduling_slot`, audit in same transaction
    ├── integration/test_concurrent_holds_postgres.py      ✅  two holds on one slot: second waits on the lock then gets `conflict`; fails without the lock
    ├── integration/test_email_outbox.py                   ✅  recording dispatcher: nothing before commit, one dispatch after, none on rollback; `send_email` run in-process reaches Mailpit
    ├── fakes/scheduling.py                                ✏️  InMemorySlotHolds; slots carry their clinician
    └── fakes/world.py                                     ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d`; migrations; seed referential | PostgreSQL, Redis, Mailpit up | system |
| Happy path | hold + verify through the container | rows in `booking_*`, slot gone from `scheduling_slot`, audits, confirmation in Mailpit | system |
| Edge case | hold expired, job not run | `GET` of free slots returns the slot again | system |
| Edge case | two concurrent holds | one `conflict`, waiter observed in `pg_stat_activity` | system |
| Edge case | delete an appointment type or clinician profile having appointments | `has_dependents` lists them | system |
| Teardown | test transaction rollback; rate-limit keys under the test prefix flushed | baseline | system |

## Tasks to do
### `1)` Models and repositories
> Booking persisted with the indexes the slot query needs.

1. Models, migration, repositories, queries; identity migration and repository fields.
2. Contract suites fake vs real.

### `2)` Cross-context adapters
> Replace the three null adapters; scheduling sees holds.

1. Scheduling `SlotHolds` port and `FindFreeSlots` filtering; delete `scheduling/infrastructure/no_appointments_yet.py` after wiring its replacement.
2. Identity `BookingUpcomingAppointments`, organisation dependents from booking.
3. Booking adapters over organisation, identity, scheduling inbound ports; locks.

### `3)` Redis, Celery, settings
> Limits, emails after commit, expiry every minute.

1. `RedisRateLimiter`; `CeleryEmailOutbox`; tasks and beat; settings and `.env.example`.
2. Concurrency test per testing.md; email outbox integration test.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | contract suites pass on fake and real |
| 2 | existing `tests/features/scheduling` and `tests/features/organisation` scenarios still green; expired hold frees the slot without the job |
| 3 | `uv run pytest -m integration tests/integration tests/contracts` green; concurrency test fails with `select_for_update` removed |
