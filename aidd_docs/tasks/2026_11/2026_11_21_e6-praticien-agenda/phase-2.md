---
status: pending
---

# Instruction: Annulation, déplacement et réservation par le praticien
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/booking/
│   ├── domain/booking_rules.py                                  ✏️  `reschedule_violations(for_patient=...)`
│   ├── application/ports/inbound.py                             ✏️  cancel/reschedule take `actor_id`; `BookForPatient`
│   ├── application/use_cases/cancel_appointment.py              ✏️  guard by actor, 24 h for patients only, audit actor
│   ├── application/use_cases/reschedule_appointment.py          ✏️  guard by actor, staff rules = availability only
│   ├── application/use_cases/placement.py                       ✏️  `for_patient`, `actor`, `room_id`
│   └── application/use_cases/book_for_patient.py               ✅  clinician books in own calendar, source `STAFF`
├── src/drlibre/scheduling/
│   ├── application/ports/inbound.py                             ✏️  `FindFreeWeek.week(..., for_patient: bool = True)`
│   └── application/use_cases/find_free_week.py                  ✏️  lead time clip only for patients
├── src/drlibre/interfaces/web/views/portal.py                   ✏️  pass `actor_id`
├── src/drlibre/interfaces/api/appointments.py                   ✏️  pass `actor_id` (patient behaviour unchanged)
├── src/drlibre/bootstrap/container.py                           ✏️  wire `BookForPatient`
└── tests/
    ├── features/booking/{le_praticien_annule_un_rdv_avec_un_motif,le_praticien_deplace_un_rdv,le_praticien_reserve_un_rdv_par_l_api}.feature ✅
    ├── use_cases/booking/test_le_praticien_{annule_un_rdv_avec_un_motif,deplace_un_rdv,reserve_un_rdv_par_l_api}.py ✅
    └── use_cases/scheduling/…                                   ✏️  free week without lead time for staff
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | clinician, patient, appointments today and next week | ready | system |
| Happy path | clinician cancels own appointment starting in 2 h with a reason | `CANCELLED`, time and reason stored, notification « RDV annulé » and email, audit without reason | system |
| Edge case | cancel without reason, from `COMPLETED`, another clinician's | `invalid_input`, `invalid_transition`, `forbidden` | system |
| Happy path | clinician reschedules to a free slot within 120 min | moved, room kept if free, « RDV déplacé » and email | system |
| Edge case | reschedule to a non-slot, onto the patient's other appointment, no room free, from `CHECKED_IN` | `outside_availability`, `conflict`, `no_room_available`, `invalid_transition` | system |
| Happy path | clinician books an active patient for a type not bookable online in 30 min | `BOOKED`, source `STAFF`, end from duration, « RDV réservé » and email | system |
| Edge case | other clinician named, inactive patient, type of another department, inactive room | `forbidden`, `forbidden`, `not_found`, `not_found` | system |
| Regression | patient cancels / reschedules within 24 h | still `cancellation_window_closed` | system |
| Teardown | fakes discarded | baseline | system |

## Tasks to do
### `1)` Actor-aware cancel and reschedule
> One use case per action for every actor.

1. Replace `patient_id` by `actor_id`; resolve `clinician_of_user(actor_id)`: profile → `own_clinician_appointment`, none → `own_appointment` (patient).
2. Cancel: `cancel_violations` only for the patient; audit actor = `actor_id`.
3. Reschedule: `reschedule_violations(for_patient=...)`; `for_patient=False` keeps only `outside_availability`.
4. Update callers in `views/portal.py`, `api/appointments.py`.

### `2)` Staff placement
> §5.3 staff bound only by availability and conflicts.

1. `Placement.place(..., for_patient: bool, actor: Id, room_id: Id | None)`; `refuse_rule_violations` uses `for_patient`; `_booked_entry` actor = `actor`.
2. Named room: active room of the type's department, else `not_found`; free under `lock_rooms`, else `conflict`.
3. `BookForPatientUseCase`: actor's profile as clinician, other `clinician_id` `forbidden`, `refuse_non_patient(patient_id)`, source `STAFF`.

### `3)` Staff week strip
> No 120-min clip for the clinician.

1. `FindFreeWeek.week(..., for_patient=True)`; staff clip at `now`.

### `4)` Acceptance
> Stories annule, déplace, réserve (the API bullets are covered in phase 4; the waitlist bullet arrives with E5).

1. Three `.feature` files with steps on fakes.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | clinician cancels and reschedules within 24 h; patient E4 scenarios unchanged and green |
| 2 | staff booking ignores lead time, open count and online flag; `outside_availability` and `conflict` still apply; source `STAFF` |
| 3 | staff free week contains a slot in 30 min; patient week does not |
| 4 | `uv run pytest tests/use_cases -m "not integration"` green |
