---
status: done
---

# Instruction: Statuts sans `CONFIRMED`, champs d'annulation, garde-fous PostgreSQL
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── config/settings.py                                           ✏️  `django.contrib.postgres` in `INSTALLED_APPS`
├── scripts/seed.py                                              ✏️  load seed writes `BOOKED` only, cancelled rows carry `cancelled_at` and reason
├── src/drlibre/
│   ├── shared_kernel/booking_policy.py                          ✏️  `CANCELLATION_WINDOW`, `MAX_OPEN_ONLINE` moved here
│   ├── scheduling/domain/appointment.py                         ✏️  `CONFIRMED` removed
│   └── booking/
│       ├── domain/appointment.py                                ✏️  `CONFIRMED` removed; `cancelled_at`, `cancellation_reason`
│       ├── domain/booking_rules.py                              ✏️  imports policy numbers; `CANCELLATION_WINDOW_CLOSED`
│       ├── application/ports/outbound.py                        ✏️  `Appointments.save`, `excluding` on `conflicting_resources` and `busy_rooms`
│       └── infrastructure/
│           ├── repositories.py                                  ✏️  `save`, `excluding`, `IntegrityError` of the exclusion → `conflict`
│           └── django/
│               ├── models.py                                    ✏️  new fields, `ExclusionConstraint` ×2, `CheckConstraint` ×3, hold `end > start`
│               └── migrations/0002_appointment_guards.py        ✅  `BtreeGistExtension`, `CONFIRMED`→`BOOKED` data step, fields, constraints
└── tests/
    ├── fakes/booking.py                                         ✏️  `save`, `excluding`
    ├── contracts/test_booking_repositories.py                   ✏️  `CONFIRMED` case replaced; `save` and `excluding` contracts
    ├── use_cases/booking/conftest.py                            ✏️  `CONFIRMED` step replaced by `CHECKED_IN`
    └── integration/test_appointment_guards_postgres.py          ✅  each constraint refuses its bad row; active overlap → `conflict`
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d`, migrate | `btree_gist` installed, migration 0002 applied | system |
| Happy path | insert two non-overlapping active appointments of one clinician, then cancel one with time and reason | both stored; cancelled row valid | system |
| Edge case | insert overlapping active appointments for one clinician, then for one patient | second refused, adapter raises `conflict` | system |
| Edge case | overlap where the first is `CANCELLED` or `NO_SHOW` | accepted | system |
| Edge case | `end <= start` on appointment or hold; `CANCELLED` without reason; reason without `CANCELLED` | refused by the check | system |
| Edge case | `python -m scripts.seed --size load` on a fresh volume | completes with no constraint error | cli |
| Teardown | test transaction rolled back | baseline restored | system |

## Tasks to do
### `1)` Remove `CONFIRMED`
> One active-but-not-yet-checked-in status left: `BOOKED`.

1. Drop the member from both enums; replace its uses in seed and tests (`CHECKED_IN` where a second active status is needed).
2. Data step in migration 0002: `CONFIRMED` → `BOOKED`; stored `CANCELLED` rows get `cancelled_at = start` and reason « Annulé avant E4 »; then the constraints.

### `2)` Cancellation fields and policy constants
> Appointment records when and why it was cancelled.

1. `Appointment.cancelled_at: datetime | None`, `cancellation_reason: str | None`; model fields (reason ≤ 500, null).
2. Move `CANCELLATION_WINDOW`, `MAX_OPEN_ONLINE` to `shared_kernel/booking_policy.py`; add `BookingRule.CANCELLATION_WINDOW_CLOSED`.

### `3)` Repository writes for cancel and reschedule
> Later phases update an appointment and check conflicts ignoring it.

1. `Appointments.save(appointment)` replaces the stored row (docstring: absent id is refused by the adapter).
2. `excluding: Id | None = None` on `conflicting_resources` and `busy_rooms`, in port, fake and Django adapter; contract tests on both.

### `4)` PostgreSQL guards
> Second defence behind the locks.

1. `django.contrib.postgres` installed; `TsTzRange` custom `Func` beside the models; `BtreeGistExtension()` then `ExclusionConstraint` `appointment_clinician_no_overlap` and `appointment_patient_no_overlap` (`TsTzRange(start, end, '[)')` overlaps, id equal, condition status not in `CANCELLED`, `NO_SHOW`).
2. `CheckConstraint`: `appointment_end_after_start`, `booking_hold_end_after_start`, `appointment_status_known`, `appointment_cancellation_consistent`.
3. `DjangoAppointments.add/save` map the exclusion `IntegrityError` to `DomainError(CONFLICT, details.resources)`.
4. Load seed: cancelled rows get `cancelled_at` and a reason; reseed on a fresh volume, and migrate a volume holding the E3 load seed, to prove both.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `grep -rn CONFIRMED src scripts tests` finds only migrations; full suite green |
| 2 | domain builds a cancelled appointment with time and reason; rule value `cancellation_window_closed` exists |
| 3 | contract suite passes on fake and Django for `save` and `excluding` |
| 4 | each guard test fails with the constraint removed; overlap gives `conflict`; load seed completes |
