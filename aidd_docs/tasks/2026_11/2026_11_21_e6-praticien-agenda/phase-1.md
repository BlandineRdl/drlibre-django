---
status: done
---

# Instruction: Garde praticien, statuts et notes cliniques
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/booking/
│   ├── domain/appointment.py                                    ✏️  `checked_in()`, `completed()`, `no_show()`, `clinical_notes`, `MAX_CLINICAL_NOTES = 5000`
│   ├── domain/booking_rules.py                                  ✏️  `ClinicianAction`, `clinician_actions(appointment)`
│   ├── application/ports/inbound.py                             ✏️  `CheckInAppointment`, `CompleteAppointment`, `MarkNoShow`, `WriteClinicalNotes`
│   ├── application/ports/outbound.py                            ✏️  `BookingDirectory.clinician_of_user`
│   ├── application/use_cases/own_clinician_appointment.py       ✅  guard: `not_found`, `forbidden`
│   ├── application/use_cases/status_change.py                   ✅  shared helper: guard, locks, re-read, save, audit
│   ├── application/use_cases/{check_in_appointment,complete_appointment,mark_no_show,write_clinical_notes}.py ✅
│   ├── infrastructure/directory.py                              ✏️  `clinician_of_user` via `ReferenceQueries.clinician_profile_of`
│   ├── infrastructure/repositories.py                           ✏️  map `clinical_notes`
│   └── infrastructure/django/{models.py,migrations/0004_appointment_clinical_notes.py} ✏️✅
├── src/drlibre/bootstrap/container.py                           ✏️  wire the four use cases
└── tests/
    ├── fakes/booking.py                                         ✏️  `FixedBookingDirectory.clinician_of_user`, notes kept by `InMemoryAppointments`
    ├── fakes/world.py                                           ✏️  wiring
    ├── contracts/test_booking_repositories.py                   ✏️  notes round trip
    ├── contracts/test_booking_directory.py                      ✅  `clinician_of_user` fake vs `OrganisationBookingDirectory`
    ├── features/booking/{le_praticien_fait_avancer_le_statut_d_un_rdv,le_praticien_tient_les_notes_cliniques_d_un_rdv}.feature ✅
    └── use_cases/booking/{test_le_praticien_fait_avancer_le_statut_d_un_rdv.py,test_le_praticien_tient_les_notes_cliniques_d_un_rdv.py,steps_clinician.py,support.py} ✅✅✅✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | world with two clinicians, one patient, `BOOKED` appointments | ready | system |
| Happy path | check in then complete own `BOOKED` appointment | `CHECKED_IN` then `COMPLETED`; two audit entries `{from, to}` | system |
| Happy path | mark own `BOOKED` no-show | `NO_SHOW`; slot freed; no notification | system |
| Edge case | complete a `BOOKED`, check in a `COMPLETED` | `invalid_transition` with `status` | system |
| Edge case | act on another clinician's appointment | `forbidden`; unknown id `not_found` | system |
| Happy path | write notes ≤ 5000 | stored; audit names `clinical_notes`, never the text | system |
| Edge case | notes of 5001 characters | `invalid_input` on `clinical_notes` | system |
| Teardown | fakes discarded | baseline | system |

## Tasks to do
### `1)` Transitions and notes in the domain
> §5.6 table on `Appointment`.

1. Add `checked_in()`, `completed()`, `no_show()` raising `_refused_transition()` outside `BOOKED`/`CHECKED_IN`/`BOOKED`.
2. Add `clinical_notes: str | None` and `with_notes(text)` validating ≤ 5000 after strip, empty → `None`.
3. Add `ClinicianAction` and `clinician_actions(appointment)` from the same guards (`cancellable`, `movable`).

### `2)` Clinician guard
> The appointment's clinician only.

1. Add `BookingDirectory.clinician_of_user(user_id) -> Id | None`, implement in `OrganisationBookingDirectory` and `FixedBookingDirectory`, contract both.
2. Write `own_clinician_appointment(appointments, appointment_id, profile_id)`; no profile → `forbidden` « Réservé aux praticiens ayant un profil. ».

### `3)` Status use cases
> Check in, complete, no-show.

1. `StatusChange.apply(actor_id, appointment_id, transition)`: guard, `lock_clinician`, `lock_patient`, re-read, transition, `save`, audit `booking.appointment_status_changed` `{from, to}` with actor.
2. `MarkNoShow` also calls `SlotRefresh.refresh(clinician)`.
3. Wire in `container.py` and `world.py`.

### `4)` Notes use case and storage
> Saved separately, visible to the clinician only.

1. `clinical_notes` nullable `TextField` on `AppointmentRecord`, migration `0003`, repository mapping.
2. `WriteClinicalNotes.execute(actor_id, appointment_id, text)`: guard, write, audit `booking.appointment_notes_written` `{fields: ("clinical_notes",)}`.

### `5)` Acceptance
> One `.feature` per Story, Scenario names = acceptance bullets (the API bullet is covered in phase 4).

1. `le_praticien_fait_avancer_le_statut_d_un_rdv.feature`, `le_praticien_tient_les_notes_cliniques_d_un_rdv.feature` with steps on fakes.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | every §5.6 pair accepted, every other pair `invalid_transition` with the current status |
| 2 | other clinician `forbidden`, unknown id `not_found`, contract green on fake and real |
| 3 | status changes audited `{from, to}` without personal data, no notification row, `NO_SHOW` frees the slot |
| 4 | notes > 5000 `invalid_input`; audit metadata holds `fields` only; migration applies on compose |
| 5 | `uv run pytest tests/use_cases/booking tests/contracts -m "not integration"` and integration contracts green |
