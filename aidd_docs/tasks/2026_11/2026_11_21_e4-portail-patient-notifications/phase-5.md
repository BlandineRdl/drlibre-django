---
status: pending
---

# Instruction: Lecture des RDV du patient, `GET /appointments`, profil
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/
│   ├── booking/
│   │   ├── application/ports/inbound.py                         ✏️  `ListPatientAppointments`, `AgendaEntry`, `AgendaFilter`
│   │   ├── application/ports/outbound.py                        ✏️  `PatientAgenda`
│   │   ├── application/use_cases/list_patient_appointments.py   ✅  upcoming / past split and order, allowed actions
│   │   └── infrastructure/patient_agenda.py                     ✅  `SqlPatientAgenda`: one joined query, filters clinician, status, range
│   ├── identity/
│   │   ├── domain/user.py                                       ✏️  `with_profile(phone, birth_date)`; phone and birth date rules
│   │   ├── application/ports/inbound.py                         ✏️  `UpdateProfile`
│   │   └── application/use_cases/update_profile.py              ✅  audit `user.profile_updated` with changed field names
│   ├── interfaces/api/appointments.py                           ✏️  `GET /appointments`
│   └── bootstrap/container.py                                   ✏️  `list_patient_appointments`, `update_profile`
└── tests/
    ├── features/booking/le_patient_retrouve_ses_rendez_vous_a_venir_et_passes.feature ✅
    ├── features/identity/le_patient_met_a_jour_son_profil.feature ✅
    ├── use_cases/{booking,identity}/test_….py                   ✅
    ├── fakes/booking.py                                         ✏️  `InMemoryPatientAgenda`
    ├── contracts/test_patient_agenda.py                         ✅  fake vs SQL on the same rows
    └── api/test_appointments_list.py                            ✅  own only, `patient=` ignored, filters, 401 anonymous, staff `forbidden`
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | patient with `BOOKED` future, `CHECKED_IN` future, `COMPLETED`, `CANCELLED`, and another patient's appointment | ready | system |
| Happy path | list | upcoming soonest first, past latest first; every field of the Story; hospital zone named | system |
| Happy path | `GET /appointments?status=BOOKED&from=…&to=…` | only matching own rows | api |
| Edge case | `GET /appointments?patient=<other>` | own rows only | api |
| Edge case | anonymous; clinician caller | `unauthenticated`; `forbidden` | api |
| Happy path | update phone and birth date; clear phone | saved; audit holds field names only | system |
| Edge case | phone `12`, `abc1234`, 21 chars; birth date tomorrow, `2026-02-30` | `invalid_input` with the field message | system |
| Teardown | fakes or transaction discarded | baseline | system |

## Tasks to do
### `1)` Patient agenda read
> One query feeds the portal list and the API.

1. `AgendaEntry`: appointment id, status, start, end, reason, clinician name, title, specialty, hospital name, address, time zone, department, room (optional), type, allowed actions.
2. `SqlPatientAgenda` joins booking, organisation and identity tables; fake on the same contract.
3. `ListPatientAppointmentsUseCase(patient_id, filter)` returns upcoming and past per the Story.

### `2)` `GET /appointments`
> Limited to what the caller may see.

1. `identity_of(request)` as `POST /appointments`, `unauthenticated` when absent, `require_patient` so staff get `forbidden`; query `clinician`, `status`, `from`, `to`, `patient` ignored; unknown params refused per §4 only on writes.

### `3)` Profile
> Phone and birth date editable.

1. `User.with_profile`; validators `^[0-9 +()\-]{7,20}$`, ISO date not after today; empty clears.
2. `UpdateProfileUseCase(user_id, phone, birth_date)`, audit with changed names (`changed_fields`).

### `4)` Story scenarios
> Stories « retrouve » and « profil » (password bullet left to phase 6).

1. One scenario per acceptance bullet.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | contract green on fake and PostgreSQL; one SQL query per page (`django_assert_num_queries`) |
| 2 | API tests green; another patient's rows never returned |
| 3 | invalid values give `invalid_input` with the field; audit metadata holds no value |
| 4 | each acceptance bullet maps to a scenario name |
