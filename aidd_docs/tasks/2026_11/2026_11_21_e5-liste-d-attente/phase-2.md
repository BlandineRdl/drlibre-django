---
status: done
---

# Instruction: Inscription par le patient et par l'admin, lectures
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/booking/
│   ├── application/ports/inbound.py                             ✏️  `JoinWaitlist`, `WaitlistQueries` with `WaitlistRow`, `WaitlistOption`
│   ├── application/ports/outbound.py                            ✏️  `Staff.is_admin(user_id)`; `Patients.active_patient_by_email(email)`
│   ├── application/use_cases/join_waitlist.py                   ✅
│   ├── infrastructure/identity_staff.py                         ✅  `IdentityStaff`: `StaffLookup.staff_member` with role `ADMIN` and active
│   ├── infrastructure/patients.py                               ✏️  `IdentityPatients.active_patient_by_email` through `UserQueries.user_by_email`
│   └── infrastructure/waitlist_queries.py                       ✅  `SqlWaitlistQueries`
├── src/drlibre/identity/application/ports/inbound.py            ✏️  `UserQueries.user_by_email(email)`; no inbound lookup by email exists (only outbound `Users.by_email`)
├── src/drlibre/identity/infrastructure/queries.py               ✏️  its implementation
├── tests/fakes/user_queries.py                                  ✏️  same method
├── src/drlibre/bootstrap/container.py                           ✏️  `join_waitlist`, `waitlist_queries`, `BookingAdapters.staff`
└── tests/
    ├── fakes/booking.py                                         ✏️  `InMemoryStaff`, `InMemoryWaitlistQueries`, `InMemoryPatients.active_patient_by_email`
    ├── features/booking/{le_patient_s_inscrit_sur_la_liste_d_attente,l_admin_inscrit_un_patient_sur_la_liste_d_attente,l_admin_suit_la_liste_d_attente}.feature ✅
    ├── use_cases/booking/{steps_waitlist.py,test_le_patient_s_inscrit_sur_la_liste_d_attente.py,test_l_admin_inscrit_un_patient_sur_la_liste_d_attente.py} ✅
    ├── conftest.py                                              ✏️  `pytest_plugins` gains `steps_waitlist`
    ├── contracts/{test_waitlist_queries.py,test_staff.py}       ✅
    └── integration/test_l_admin_suit_la_liste_d_attente_postgres.py ✅  Story « suit » on PostgreSQL (order, filter, 20 per page, total)
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | fake world: department with an online type and an offline type, active and inactive clinicians, signed-in patient, admin, another patient | ready | system |
| Happy path | patient joins with type, preferred clinician and dates | `WAITING` entry for the session's patient, window in the hospital zone, audit `booking.waitlist_joined` with ids only | system |
| Happy path | admin adds a patient by email | `WAITING` entry for that patient, audit actor the admin | system |
| Edge case | unknown or inactive type or clinician, clinician of another department, unknown or inactive patient email | `not_found` | system |
| Edge case | patient with an offline type | `rule_violation` `type_not_bookable_online` | system |
| Edge case | `to_date` before `from_date` or before today | `invalid_input` on `to_date` | system |
| Edge case | patient names `patient_email`; clinician joins | `forbidden` | system |
| Edge case | admin list with `status=bogus` | all statuses, oldest first, page 1 | system |
| Teardown | fakes discarded | baseline | system |

## Tasks to do
### `1)` Join use case
> One unit of work: checks, entry, audit.

1. `JoinWaitlistUseCase` per plan Decisions: actor resolution (`refuse_non_patient` or `Staff.is_admin` + `active_patient_by_email`), `bookable_type`, preferred clinician of the department, online rule for a patient, window from dates in `BookableType.time_zone`, `Waitlist.add`, audit `booking.waitlist_joined` (`appointment_type_id`, `clinician_id`).
2. `IdentityStaff` adapter, `UserQueries.user_by_email` (normalised lower-case email), `IdentityPatients.active_patient_by_email`; wire in `_wire_booking`.

### `2)` Read side
> One SQL query per page.

1. `SqlWaitlistQueries.own_entries(patient_id)` newest first, `page(status, request)` oldest first with total, rows holding patient name, type, preferred clinician, window, status, offered start and hospital zone.
2. `type_options(online_only)` active types of active hospitals labelled with the hospital; `clinician_options()` active clinicians labelled with department.
3. `InMemoryWaitlistQueries` and the contract suite.

### `3)` Story scenarios
> Stories « s'inscrit », « inscrit un patient », « suit ».

1. One scenario per acceptance bullet; API bullets left to phase 7.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | refused joins write nothing; audit metadata holds no name or email |
| 2 | contract green on fake and PostgreSQL; `django_assert_num_queries(1)` per page |
| 3 | each acceptance bullet maps to a scenario name |
