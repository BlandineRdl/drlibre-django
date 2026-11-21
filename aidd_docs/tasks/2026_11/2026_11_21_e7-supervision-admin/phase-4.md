---
status: pending
---

# Instruction: API admin
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/api/
│   ├── appointments.py                                         ✏️  `GET` admin paginé, `POST` admin avec praticien, actions admin
│   ├── jobs.py                                                 ✅  `POST /jobs/reminders`
│   └── __init__.py                                             ✏️  monte le routeur jobs
└── tests/api/
    ├── test_appointment_actions.py                              ✏️  l'admin agit ; un inconnu reste `forbidden`
    ├── test_appointments_list.py                                ✏️  liste admin filtrée
    └── test_admin_endpoints.py                                  ✅  réservation admin, rappels
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | admin, praticien, patient sur la stack compose | prêt | api |
| Happy path | admin `POST /appointments/{id}/check-in`, `/complete`, `/no-show`, `/cancel`, `/reschedule` | 200 `AppointmentOut` | api |
| Happy path | admin `GET /appointments?department=…&status=BOOKED&page=2` | `{items, total, page}` | api |
| Happy path | admin `POST /appointments` avec `clinician`, `patient`, type non réservable en ligne | 201, source `STAFF` | api |
| Edge case | admin sans `clinician` | 400 `invalid_input` | api |
| Happy path | admin `POST /jobs/reminders` | 200 `{count}` | api |
| Edge case | patient ou praticien `POST /jobs/reminders` | 403 `forbidden` | api |
| Teardown | base vidée | baseline | api |

## Tasks to do
### `1)` Appointments
> Même use cases que l'écran.

1. `GET /appointments` : admin → `ListAllAppointments` avec `department`, `clinician`, `status`, `source`, `from`, `to`, `page`.
2. Actions et `POST` passent l'acteur ; les use cases décident.

### `2)` Jobs
> `POST /jobs/reminders` → `RunReminders`.

1. Routeur `jobs`, CSRF/origine comme les autres POST.

### `3)` Tests
> Réécrire l'attente « l'admin attend E7 ».

1. Paramétrage : praticien sans profil reste `forbidden`, admin réussit.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | les puces §14 des Stories annule, déplace, réserve passent par l'API |
| 2 | rôle autre qu'admin → 403 |
| 3 | `uv run pytest tests/api` vert |
