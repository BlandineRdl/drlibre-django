---
status: pending
---

# Instruction: Contexte `booking` : placement, règles, premier disponible sur fakes
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── pyproject.toml                                         ✏️  import-linter: `drlibre.booking` in the layers contract; booking core forbids identity, organisation, scheduling
├── src/drlibre/booking/
│   ├── __init__.py                                        ✅
│   ├── domain/
│   │   ├── __init__.py                                    ✅
│   │   ├── appointment.py                                 ✅  Appointment (patient, clinician, type, room?, period, status, source, reason?), Source, Status, `active`
│   │   ├── booking_rules.py                               ✅  LEAD_TIME 120 min, CANCELLATION_WINDOW 24 h, MAX_OPEN_ONLINE 3; violations for patients
│   │   └── round_robin.py                                 ✅  rank candidates: never assigned first, then elapsed × weight, then lowest id
│   └── application/
│       ├── __init__.py                                    ✅
│       ├── ports/{__init__,inbound,outbound}.py           ✅  inbound BookAppointment, BookingQueries ; outbound Appointments, BookingDirectory, FreeSlots, SlotRefresh, ScheduleLocks, Patients, BookingNotices, RoundRobinLedger
│       └── use_cases/
│           ├── __init__.py                                ✅
│           ├── placement.py                               ✅  the §5.2 steps in order, stop at first failure; room choice; audit; slot refresh
│           └── book_appointment.py                        ✅  signed-in patient; named clinician (ONLINE) or first available (ROUND_ROBIN)
├── src/drlibre/bootstrap/container.py                     ✏️  booking adapters and `book_appointment`
└── tests/
    ├── builders_booking.py                                ✅  appointment, type, clinician candidate builders
    ├── fakes/booking.py                                   ✅  InMemoryAppointments, FixedBookingDirectory, InMemoryFreeSlots, RecordingSlotRefresh, InMemoryPatients, RecordingBookingNotices
    ├── fakes/world.py                                     ✏️  booking fakes in `adapters()` and `InMemoryUnitOfWork`
    ├── features/booking/
    │   ├── une_reservation_qui_enfreint_une_regle_est_refusee_avec_son_motif.feature  ✅
    │   └── un_patient_connecte_reserve_sans_ressaisir_ses_informations.feature        ✅
    ├── use_cases/booking/
    │   ├── __init__.py                                    ✅
    │   ├── test_une_reservation_qui_enfreint_une_regle_est_refusee_avec_son_motif.py  ✅
    │   └── test_un_patient_connecte_reserve_sans_ressaisir_ses_informations.py        ✅
    └── properties/test_round_robin.py                     ✅  Hypothesis: order total and stable, never-assigned first, weight monotone
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | FakeWorld with a department, two clinicians with free slots, an online type needing a room, a signed-in patient | world ready, clock 2026-11-20 10:00 UTC | system |
| Happy path | patient books a free slot of a named clinician | appointment `BOOKED`, source `ONLINE`, end = start + duration, default room, audit `booking.appointment_booked`, slot refresh called, confirmation notice queued | system |
| Happy path | patient books without clinician | candidate ranked first gets it, source `ROUND_ROBIN`, its last assignment set to now | system |
| Edge case | inactive type, other department, overlap clinician/patient, start < now + 120 min, 3 open online bookings, type not online, start not a free slot, no room free | `not_found`, `conflict` with resources, `rule_violation` with rules, `no_room_available`, in that order, nothing written | system |
| Edge case | patient body names another patient or a room; end time sent | ignored or refused `invalid_input`; identity from the session only | system |
| Edge case | first available with no candidate | `no_clinician_available` | system |
| Teardown | FakeWorld discarded per scenario | no shared state | system |

## Tasks to do
### `1)` Domain
> Pure rules a Hypothesis property can test.

1. `Appointment`, `Source` (`ONLINE`, `ROUND_ROBIN`, `STAFF`), `Status` (spec §3.1), `active` unless `CANCELLED`/`NO_SHOW`.
2. `booking_rules.violations(for_patient, start, now, type_online, open_online_count, is_free_slot)` returning the §5.3 rule codes in the spec's order.
3. `round_robin.rank(candidates, now)`; candidate = clinician id, weight, last assigned at.

### `2)` Ports and placement
> One placement service every booking path calls.

1. Outbound ports in `ports/outbound.py`; `BookingDirectory` gives type (active, online, duration, buffer, needs room, department), clinician (active user, department, default room, weight, last assigned), department rooms in code order.
2. `FreeSlots.is_free(clinician, type, start, *, ignoring_hold)` and `FreeSlots.candidates_at(type, start)`; implemented later over scheduling's new `SlotAvailability` inbound port.
3. `placement.py`: lock clinician (and patient), steps 1→6 of §5.2, room choice of step 5, `Appointments.add`, audit, `SlotRefresh.refresh(clinician)`, `BookingNotices.confirmed(appointment)` inside one unit of work.
4. `book_appointment.py`: patient identity from the caller's session id only; first available ranks candidates and books the first; sets last assignment through outbound `RoundRobinLedger.record(clinician, at)`, backed in phase 3 by organisation's `RecordRoundRobinAssignment`.

### `3)` Wiring and tests
> Scenarios mirror the acceptance bullets.

1. Fakes with trivial behaviour; add them to `FakeWorld.adapters()` and the uow snapshot.
2. Feature files in French, one scenario per acceptance bullet of the two Stories (placement part); round robin property test.
3. Container wires null-free fakes in tests and placeholder real adapters to be completed in phase 3.
4. import-linter contracts for `drlibre.booking`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | round robin property: never-assigned clinicians precede others; larger elapsed × weight first; ties by lowest id; rule order matches §5.3 |
| 2 | each failing step returns its code and writes nothing; success writes appointment, audit and refresh in one uow |
| 3 | `uv run pytest tests/use_cases/booking tests/properties/test_round_robin.py` green; `uv run lint-imports` green |
