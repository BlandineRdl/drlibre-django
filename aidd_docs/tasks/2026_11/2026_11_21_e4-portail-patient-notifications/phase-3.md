---
status: pending
---

# Instruction: Annulation et déplacement par le patient
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/
│   ├── booking/
│   │   ├── application/ports/inbound.py                         ✏️  `BookedPeriod.id`, `CancelAppointment`, `RescheduleAppointment`
│   │   ├── infrastructure/queries.py                            ✏️  `periods_of` fills `id`
│   │   ├── domain/appointment.py                                ✏️  `cancelled(at, reason)`, `moved(start, duration, room_id)`, transition guards → `invalid_transition`
│   │   ├── domain/booking_rules.py                              ✏️  `reschedule_violations`, `cancel_violations`, `allowed_actions`
│   │   ├── application/use_cases/{cancel_appointment,reschedule_appointment}.py ✅
│   │   ├── application/use_cases/placement.py                   ✏️  room choice preferring a given room; checks with `excluding`
│   │   ├── application/ports/outbound.py                        ✏️  `FreeSlots.is_free(..., ignoring_appointment)`
│   │   └── infrastructure/free_slots.py                         ✏️  passes `ignoring_appointment`
│   ├── scheduling/
│   │   ├── domain/appointment.py                                ✏️  scheduling `Appointment` gains `id`
│   │   ├── application/ports/{inbound,outbound}.py              ✏️  `ignoring_appointment` on `IsSlotFree`, `FindFreeSlots`
│   │   ├── application/use_cases/{is_slot_free,find_free_slots,open_slots,refresh_slots}.py ✏️  on-the-fly `SlotEngine` slots without the ignored appointment
│   │   └── infrastructure/booking_appointments.py               ✏️  maps booking's `BookedPeriod.id` into it
│   └── bootstrap/container.py                                   ✏️  `cancel_appointment`, `reschedule_appointment`
└── tests/
    ├── features/booking/{le_patient_annule_un_rendez_vous,le_patient_deplace_un_rendez_vous}.feature ✅
    ├── use_cases/booking/{conftest.py,test_le_patient_annule_un_rendez_vous.py,test_le_patient_deplace_un_rendez_vous.py} ✏️✅
    ├── properties/test_slot_engine.py                           ✏️  ignoring an appointment equals refreshing without it
    ├── contracts/test_clinician_appointments.py                 ✏️  ids
    └── integration/test_concurrent_patient_changes_postgres.py  ✅  two reschedules to one slot: one `conflict`; two cancels: one `invalid_transition`; lock waiter seen
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | fake world: patient with a `BOOKED` appointment in 3 days, free slots that week, two rooms | ready | system |
| Happy path | cancel with a reason | `CANCELLED` with time and reason; slot freed; « RDV annulé » row; one email without reason; audit without reason | system |
| Happy path | reschedule to a free slot overlapping the current appointment's time | moved, end recomputed, room kept; « RDV déplacé » with new time; email; audit | system |
| Edge case | cancel without reason | `invalid_input` on `reason` | system |
| Edge case | cancel or reschedule under 24 h | `rule_violation` `cancellation_window_closed`; nothing written or notified | system |
| Edge case | cancel `COMPLETED`/`CANCELLED`/`NO_SHOW`; reschedule `CHECKED_IN` | `invalid_transition` with current status | system |
| Edge case | reschedule: new start < 120 min, type offline, start not a free slot | `rule_violation` listing each rule | system |
| Edge case | reschedule overlapping another appointment of patient, clinician | `conflict` with resources | system |
| Edge case | current room taken | default room, else first free, else `no_room_available` | system |
| Edge case | another patient's appointment | `forbidden`; unknown `not_found` | system |
| Teardown | fakes discarded | baseline | system |

## Tasks to do
### `1)` Domain transitions and rules
> Pure rules for cancel and reschedule.

1. `Appointment.cancelled(at, reason)` from `BOOKED` or `CHECKED_IN`, else `invalid_transition` with `details.status`; `moved(...)` from `BOOKED` only.
2. `booking_rules.cancel_violations(start, now)`, `reschedule_violations(current_start, new_start, now, type_online, is_free_slot)` in §5.3 order; `allowed_actions(appointment, now) -> frozenset` for the portal.

### `2)` Slots ignoring an appointment
> The appointment's own time is free for its reschedule.

1. Booking's `BookedPeriod` carries `id` (`queries.py`); scheduling's domain `Appointment` gains `id`, mapped in `booking_appointments.py`.
2. Extract `RefreshSlotsUseCase`'s computation into a function reused by `IsSlotFree` and `FindFreeSlots` when `ignoring_appointment` is set (range bounded by `MAX_RANGE`), then drop held slots as `open_slots` does.
3. Hypothesis property: ignoring appointment A yields the slots a refresh without A stores.

### `3)` Use cases
> One unit of work per change: locks, checks, save, slots, audit, notice.

1. `CancelAppointmentUseCase(appointment_id, patient_id, reason)`: read for the clinician, lock clinician then patient, re-read under the locks, ownership, reason, transition, window; save; `slot_refresh`; audit `booking.appointment_cancelled` (ids only); `notices.cancelled`.
2. `RescheduleAppointmentUseCase(appointment_id, patient_id, start)`: read, lock clinician, patient, rooms; re-read under the locks; ownership; transition; rules; conflicts with `excluding`; room preferring current; save; `slot_refresh`; audit `booking.appointment_rescheduled`; `notices.rescheduled`.
3. Wire both in `_wire_booking`.

### `4)` Story scenarios and race
> Stories « annule » and « déplace ».

1. One scenario per acceptance bullet (API bullet left to phase 6).
2. PostgreSQL races per `testing.md` (reschedule vs reschedule, cancel vs cancel): each fails with the lock or the re-read removed.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | refused statuses give `invalid_transition` with the status; rules listed in spec order |
| 2 | property green; existing scheduling scenarios unchanged |
| 3 | refused cancel or reschedule writes, notifies and emails nothing |
| 4 | each acceptance bullet maps to a scenario name; race test sees a `Lock` waiter |
