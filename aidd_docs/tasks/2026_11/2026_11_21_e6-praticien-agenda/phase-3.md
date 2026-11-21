---
status: pending
---

# Instruction: Lectures praticien et historique d'audit
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/audit/
│   ├── application/ports/inbound.py                             ✏️  `AuditQueries.entries_for(entity_type, entity_id)`, ✅ `AuditRecordView(actor_id, action, at)` dataclass
│   └── infrastructure/{queries.py,django/models.py,django/migrations/0003_entry_target_index.py} ✏️✏️✅
├── src/drlibre/booking/
│   ├── application/ports/outbound.py                            ✏️  `ClinicianAgenda`, `AppointmentHistory`, row dataclasses
│   ├── application/ports/inbound.py                             ✏️  `ClinicianDay`, `ClinicianWeek`, `ClinicianAppointment`, `ClinicianPatients`, `DepartmentRoomsDay`, `ListClinicianAppointments`
│   ├── application/use_cases/clinician_reads.py                 ✅  read use cases, each guarded by the actor's profile
│   ├── infrastructure/clinician_agenda.py                       ✅  `SqlClinicianAgenda`
│   └── infrastructure/audit_history.py                          ✅  `AuditAppointmentHistory`
├── src/drlibre/bootstrap/container.py                           ✏️
└── tests/
    ├── fakes/{booking.py,audit_log.py,world.py}                 ✏️  `InMemoryClinicianAgenda`, `entries_for`
    ├── contracts/{test_clinician_agenda.py,test_audit_log.py}   ✅✏️
    ├── features/booking/{le_praticien_voit_son_agenda_du_jour,le_praticien_voit_sa_semaine_dans_le_calendrier,le_praticien_consulte_la_fiche_d_un_rdv,le_praticien_retrouve_ses_patients,le_praticien_voit_l_occupation_des_salles_du_jour}.feature ✅
    └── use_cases/booking/test_le_praticien_{…}.py               ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | two clinicians of one department, patients with past and future appointments, a time off, a held slot | ready | system |
| Happy path | day read | own rows only, grouped by local hour, counts, next free slot not held | system |
| Happy path | week read | active rows with type colour, time off blocks, no cancelled or no-show | system |
| Happy path | detail | patient name, phone, age, type, room, reason, status, notes, actions, history in `at` order | system |
| Edge case | detail of another clinician's appointment | `forbidden`; unknown `not_found` | system |
| Happy path | patients with search « mar » | only own patients matching, last `COMPLETED`, next active | system |
| Happy path | rooms day | active rooms; own rows carry patient name, others none | system |
| Edge case | day near midnight in `Europe/Paris` vs UTC | rows bucketed by hospital local day | system |
| Teardown | test database flushed | baseline | system |

## Tasks to do
### `1)` Audit read by target
> History of one appointment.

1. New `AuditRecordView(actor_id, action, at)`; `AuditQueries.entries_for(entity_type, entity_id) -> tuple[AuditRecordView, ...]` ordered by `at`; Django and fake; contract.
2. Index `(entity_type, entity_id, at)`, migration `audit.0003`.
3. Booking outbound `AppointmentHistory` and adapter `AuditAppointmentHistory`.
4. Actor shown without another lookup: « Patient » when `actor_id` is the appointment's patient, « Praticien » when it is the clinician's user, else « Personnel »; metadata never shown.

### `2)` `ClinicianAgenda` SQL read port
> One query per page, joined like `SqlPatientAgenda`.

1. `day(profile_id, start, end)`, `week(profile_id, start, end)`, `detail(appointment_id)`, `patients(profile_id, name_like, page, now)`, `room_day(department_id, start, end)`, `next_free_slot(profile_id, after, now)`.
2. Rows carry patient full name, phone, birth date, type name and colour, room label, status, reason; detail adds clinical notes and the clinician's user id.
3. Time off is not read here: the calendar view takes it from scheduling's inbound `AvailabilityQueries.time_offs_of(profile_id)`, as the admin week calendar does (`views/console_clinicians.py`).
4. Fake `InMemoryClinicianAgenda` over the in-memory stores; contract fake vs SQL.

### `3)` Read use cases
> Guarded by the actor's profile, time zone of the hospital.

1. Day, week, detail (guard + `clinician_actions` + history), patients, rooms day, `ListClinicianAppointments` for `GET /appointments`.
2. Wire in `container.py` and `world.py`.

### `4)` Acceptance
> Stories agenda du jour, semaine, fiche, patients, salles (screen bullets are proved in phases 5 and 6).

1. Five `.feature` files on fakes; PostgreSQL integration tests for the SQL time-zone and held-slot edges.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | entries of one appointment in time order; fake equals Django; migration applies |
| 2 | contract suite green on fake and PostgreSQL; no other clinician's patient data in any row except `room_day` occupancy without name |
| 3 | other clinician `forbidden`, unknown `not_found`, non-clinician `forbidden` |
| 4 | `uv run pytest tests/use_cases tests/contracts` green |
