---
status: done
---

# Instruction: API des actions praticien
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/api/
│   ├── appointments.py                                          ✏️  check-in, complete, no-show; cancel/reschedule for the clinician; `GET` for the clinician; `POST` with `patient`, `room`
│   └── booking.py                                               ✏️  `BookingIn` optional `patient`, `room`
└── tests/api/
    ├── test_clinician_appointment_actions.py                    ✅
    └── test_appointment_actions.py                              ✏️  patient naming a patient or room `forbidden`; admin still `forbidden`
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | clinician and patient sessions, appointments | ready | api |
| Happy path | `POST /appointments/{id}/check-in`, `/complete`, `/no-show` | 200 with new status | api |
| Edge case | forbidden transition | 409 `invalid_transition` with `status` | api |
| Happy path | `POST /appointments/{id}/cancel` `{reason}`, `/reschedule` `{start}` by the clinician | 200; patient notified | api |
| Happy path | `POST /appointments` `{patient, type, start}` by the clinician | 201 `BOOKED`, source `STAFF` | api |
| Edge case | clinician omits `patient`, names another clinician; patient names `room` | `invalid_input`, `forbidden`, `forbidden` | api |
| Happy path | `GET /appointments?clinician=<other>` by the clinician | own rows only, no notes | api |
| Edge case | other clinician's appointment; cross-origin POST; admin caller | `forbidden`; refused by `SameOriginMiddleware`; `forbidden` | api |
| Teardown | test client discarded | baseline | api |

## Tasks to do
### `1)` Status routes
> §14 check-in, complete, no-show.

1. Three routes, `auth=None` + `identity_of(request)`, `unauthenticated` when absent, calling the phase 1 use cases.

### `2)` Open cancel, reschedule and list to the clinician
> Patient behaviour unchanged.

1. Remove `require_patient` from cancel and reschedule routers; pass `actor_id`.
2. `GET /appointments`: clinician → `ListClinicianAppointments`; patient → unchanged; other roles `forbidden`.

### `3)` Staff booking body
> §5.4.

1. `BookingIn` gains `patient: UUID | None`, `room: UUID | None` (`extra="forbid"` kept).
2. Clinician → `BookForPatient`; patient naming another `patient` or any `room` → `forbidden`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | the API bullet of « fait avancer le statut » holds; same error codes as the use cases |
| 2 | API bullets of « annule » and « déplace » hold; E4 API tests still green |
| 3 | API bullets of « réserve par l'API » hold; end still never accepted |
