---
status: pending
---

# Instruction: Domaine et stockage de la liste d'attente
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/booking/
│   ├── domain/waitlist.py                                       ✅  `WaitlistStatus`, `WaitlistEntry` (join, offered, booked, back_to_waiting, expired, fits, acceptable_by_patient), `oldest`
│   ├── application/ports/outbound.py                            ✏️  `Waitlist` port; `BookableType.time_zone`
│   ├── infrastructure/django/models.py                          ✏️  `WaitlistEntryRecord`
│   ├── infrastructure/django/migrations/0003_waitlist.py        ✅
│   ├── infrastructure/repositories.py                           ✏️  `DjangoWaitlist`
│   ├── infrastructure/directory.py                              ✏️  `time_zone` of the type's hospital
│   └── infrastructure/queries.py                                ✏️  waitlist entries in `dependents_of_type`, `dependents_of_clinician`, `any_for_user`
├── src/drlibre/bootstrap/container.py                           ✏️  `BookingAdapters.waitlist`
└── tests/
    ├── fakes/booking.py                                         ✏️  `InMemoryWaitlist`; `FixedBookingDirectory` time zone
    ├── fakes/world.py                                           ✏️  wires `InMemoryWaitlist` into adapters and the unit of work
    ├── properties/test_waitlist_entry.py                        ✅  transitions and `fits`
    ├── contracts/test_waitlist.py                               ✅
    └── integration/test_waitlist_guards_postgres.py             ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | entries built by hand-written builders; PostgreSQL for the real adapter | ready | system |
| Happy path | `WAITING` → `OFFERED` → `BOOKED`; `OFFERED` → `WAITING`; `WAITING` → `EXPIRED` | status and offered link follow | system |
| Edge case | any other transition | `invalid_transition` with the current status | system |
| Edge case | window boundaries: start at `earliest`, end at `latest`, one minute outside | fits, fits, does not fit | system |
| Edge case | two `OFFERED` rows on one appointment, `latest <= earliest`, unknown status | refused by PostgreSQL; the adapter maps the unique hit to `conflict` | system |
| Edge case | delete a type, clinician profile or patient user with an entry | `has_dependents` lists « Liste d'attente » | system |
| Teardown | test database flushed | baseline | system |

## Tasks to do
### `1)` Domain
> Pure entry with its transitions.

1. `WaitlistEntry.join(*, patient_id, appointment_type_id, clinician_id, earliest, latest, at)` refuses `latest <= earliest`.
2. `offered(appointment_id)` from `WAITING`; `booked()` from `OFFERED`; `back_to_waiting()` from `OFFERED` clears the link; `expired()` from `WAITING`; else `invalid_transition` with `details.status`.
3. `fits(start, end)`, `matches(appointment_type_id, clinician_id, start, end)`, `acceptable_by_patient(offered_start, now)` using `BOOKING_LEAD_TIME` from `shared_kernel/booking_policy.py`; `oldest(entries)` by `created_at` then id.
4. Hypothesis properties on transitions and window boundaries.

### `2)` Port, table, adapter, fake
> One storage, kept identical by its contract.

1. `Waitlist` port: `add`, `save`, `get`, `get_locked`, `candidates_locked(appointment_type_id, clinician_id, start, end, excluding_patient)`, `holds_offer(appointment_id)`, `expiring_locked(now)` (`WAITING` past `latest`, `OFFERED` whose offered appointment starts at or before now, with that start).
2. `WaitlistEntryRecord`: FK `PROTECT` to type and clinician profile (nullable), `patient_id` UUID, `offered_appointment` FK to appointment nullable; checks `latest > earliest`, status in the four values, `offered_appointment` set iff `OFFERED`; partial unique on `offered_appointment` where `OFFERED`; index on `(status, appointment_type, created_at)`.
3. `DjangoWaitlist` with `select_for_update` on the locked reads; `save` in a savepoint (`transaction.atomic()`, as `_overlap_is_conflict` in `repositories.py:38-52`), unique hit → `DomainError(CONFLICT, ..., {"resources": ["waitlist_entry"]})`.
4. `InMemoryWaitlist` (`.rows`), wired in `FakeWorld` and its unit of work; contract suite over both.

### `3)` Directory and dependents
> Hospital zone of a type; entries block deletes.

1. `BookableType.time_zone` from the department's hospital in the directory adapter and fake.
2. `dependents_of_type`, `dependents_of_clinician`, `any_for_user` add `Dependent("waitlist_entry", id, "Attente du <date>")`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | properties green; refused transitions carry the current status |
| 2 | contract green on fake and PostgreSQL; each guard test fails with its constraint removed; second `OFFERED` on one appointment gives `conflict` |
| 3 | deleting a type with an entry gives `has_dependents` listing it; existing organisation scenarios unchanged |
