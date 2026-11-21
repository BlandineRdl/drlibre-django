---
objective: "Le praticien connecté pilote son agenda du jour et de la semaine, fait avancer, annule, déplace et réserve ses RDV, tient ses notes, voit ses patients et les salles, sans jamais voir les RDV d'un autre praticien."
status: in-progress
---

# Plan: E6 - Le praticien pilote sa journée et ses rendez-vous
Source: GitHub issue #9, `aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md` et ses 10 Stories `aidd_docs/backlog/stories/le-praticien-*.md` liées à cet Epic ; spec §3.1, §4, §5.2, §5.3, §5.4, §5.6, §9, §11, §14, §16 ; questions ouvertes E6 de `aidd_docs/backlog/open-questions.md`

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | Garde praticien, statuts et notes cliniques | [`phase-1.md`](./phase-1.md) | none |
| 2 | Annulation, déplacement et réservation par le praticien | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Lectures praticien et historique d'audit | [`phase-3.md`](./phase-3.md) | 1 |
| 4 | API des actions praticien | [`phase-4.md`](./phase-4.md) | 2, 3 |
| 5 | Écrans Aujourd'hui, Calendrier et fiche RDV | [`phase-5.md`](./phase-5.md) | 2, 3 |
| 6 | Écrans Patients et Salles | [`phase-6.md`](./phase-6.md) | 3 |
| 7 | Seed, parcours end-to-end, documentation, gates | [`phase-7.md`](./phase-7.md) | 4, 5, 6 |

## External sources
| URL | What it settled |
| --- | --- |
| https://docs.djangoproject.com/en/6.1/ref/models/indexes/ | `models.Index(fields=["entity_type", "entity_id", "at"])` on the audit record; the append-only triggers fire on `UPDATE`, `DELETE`, `TRUNCATE` only, so `CREATE INDEX` passes |
| https://www.w3.org/WAI/WCAG22/Understanding/use-of-color.html | the type colour in the calendar is never the only cue: the cell also names the type |
| https://www.w3.org/WAI/WCAG22/Understanding/language-of-parts.html | « Not your appointment » and « Occupied » kept verbatim from the Stories, wrapped in `lang="en"` |

## Impact
| Category | Verdict and evidence | Handled in |
| --- | --- | --- |
| Runtime | none new: PostgreSQL, Redis, Celery and Mailpit already carry the E4 emails (`OutboxBookingNotices`); migrations `booking.0003` (notes) and `audit.0003` (index) run in the compose entrypoint (migrate, architecture.md) | 1, 3, 7 |
| Regression | medium: `CancelAppointmentUseCase` applies `cancel_violations` unconditionally (`cancel_appointment.py:46`); `RescheduleAppointmentUseCase` applies patient rules (`reschedule_appointment.py:48-92`); `Placement.refuse_rule_violations` hard-codes `for_patient=True` (`placement.py:196`) and `_booked_entry` uses the patient as actor (`placement.py:237`); `FindFreeWeek` clips at `now + BOOKING_LEAD_TIME` (`find_free_week.py:34`); API cancel and reschedule refuse staff through `require_patient` (`interfaces/api/appointments.py:128-139`), list through `refuse_non_patient` (`list_patient_appointments.py:26`); `/workspace/` placeholder replaced (`views/areas.py:21-25`). Covered by `tests/features/booking/*`, `tests/api/test_appointment_actions.py`, `tests/contracts/test_booking_repositories.py`, rerun after each phase; no safety-net phase | 1, 2, 4, 5 |
| Architecture | booking gains a clinician guard through `BookingDirectory.clinician_of_user` (organisation `ReferenceQueries.clinician_profile_of`), status and notes use cases, a staff booking use case on `Placement`, a SQL read port `ClinicianAgenda` like `SqlPatientAgenda`; audit gains `AuditQueries.entries_for(entity_type, entity_id)`, read by booking's outbound `AppointmentHistory`; scheduling `FindFreeWeek` gains `for_patient` | 1, 2, 3 |
| Documentation | `architecture.md` (clinician guard, staff rules, audit read by target, notes column), `codebase-map.md` (workspace screens, `ClinicianAgenda`), `open-questions.md` (E6 answers from the decisions below); spec and Stories untouched | 7 |
| Merge | unverified: `feat/e5-liste-d-attente` has no commit ahead of `main` yet; E5 is expected to hook waitlist offers into `CancelAppointmentUseCase`; E6 keeps one cancel use case for every actor so such a hook covers the clinician; likely conflicts in `cancel_appointment.py`, `bootstrap/container.py`, `tests/fakes/world.py`; the waitlist bullet of « annule » is proved with E5, not here | 2 |

## Rules
| Rule | Why it applies |
| --- | --- |
| `aidd_docs/rules/00-architecture/0-context-boundaries.md`, `0-ports-and-use-cases.md` | booking reads organisation and audit through ports only; one `execute()` per use case |
| `aidd_docs/rules/00-architecture/0-interfaces-no-business-rule.md` | allowed actions computed in booking, never in templates or views |
| `aidd_docs/rules/02-programming-languages/2-python-value-objects.md` | agenda rows and notes as frozen dataclasses |
| `aidd_docs/rules/05-testing/5-acceptance-test-names.md`, user memory `test-names-mirror-acceptance` | one `.feature` per Story, Scenario names = acceptance bullets in French |
| `aidd_docs/rules/05-testing/5-fakes-and-contracts.md` | new fakes (`ClinicianAgenda`, `AuditQueries.entries_for`, `clinician_of_user`) get contract tests |
| `aidd_docs/rules/06-design-patterns/6-domain-errors.md` | `invalid_transition` with `status`, `forbidden`, `not_found`, `invalid_input` through `DomainError`; web views render them inline |
| `aidd_docs/rules/07-quality/7-counters-under-lock.md` | every status write re-reads the appointment under the clinician and patient locks |
| Every write audited in its transaction, metadata without personal data (`AuditEntry` allow-list) | status `{from, to}`, notes `{fields: ("clinical_notes",)}`, cancel without its reason |
| Lock order email, clinician, patient, rooms (architecture.md) | staff cancel, reschedule and book keep it |
| Identity from the session, end never from the caller | §4, §5.2 |
| WCAG 2.2 AA, 375 to 1440 px; presenters build ViewModels | §16 |
| One-line comments only | user CLAUDE.md |

## Decisions
| Decision | Why |
| --- | --- |
| Scope: the clinician only; admin calls on these actions keep `forbidden` until E7 | Epic excludes admin actions |
| The clinician of an appointment is resolved by `BookingDirectory.clinician_of_user(user_id) -> Id | None` (profile id); guard `own_clinician_appointment(appointments, id, profile_id)`: unknown id `not_found`, other clinician `forbidden` | §9, Story fiche; mirrors `own_appointment` |
| Transitions in `Appointment`: `checked_in()` from `BOOKED`, `completed()` from `CHECKED_IN`, `no_show()` from `BOOKED`; anything else `invalid_transition` with `status` | §5.6 table without `CONFIRMED` |
| Check-in and no-show have no time rule (allowed before the start) | open question E6; spec sets none and §4 has no code for it |
| One use case per status change (`CheckInAppointment`, `CompleteAppointment`, `MarkNoShow`) sharing a `StatusChange` helper: guard, lock clinician then patient, re-read, transition, save, audit `booking.appointment_status_changed` `{from, to}`, no notice; `NO_SHOW` rebuilds the clinician's slots (it frees the slot) | one `execute()` per use case; §5.6 no notification |
| Clinical notes: nullable `clinical_notes` `TextField` on `AppointmentRecord` (migration `booking.0003`), written only by `WriteClinicalNotes` (≤ 5000, stripped, empty clears), audit `booking.appointment_notes_written` `{fields: ("clinical_notes",)}`; never in `AppointmentOut`, `AgendaEntryOut`, emails or the patient agenda | §3.1, §9 « saved separately » = own form and use case |
| Notes stay writable in every status | open question E6; a note after `COMPLETED` is the common case |
| Cancel by the clinician: `CancelAppointmentUseCase.execute(appointment_id, actor_id, reason)` picks the guard from the actor (patient → `own_appointment` and 24 h; clinician → own guard, no 24 h); reason ≤ 500 (`MAX_CANCELLATION_REASON`); same notices; audit actor = the caller | Story; open question E6 answered by the E4 limit; one use case keeps one lock order and E5's hook |
| Reschedule by the clinician: same use case with `actor_id`; clinician rules = `outside_availability` only (`reschedule_violations(for_patient=False)`), conflicts ignoring itself, room preferring the current one | §5.3 « staff bound only by availability and conflicts » |
| Week strip for the clinician: `FindFreeWeek(..., for_patient=False)` drops the 120-min clip but keeps `now`; `?week=` within the 90-day horizon | open question E6, same navigation as the patient strip |
| Staff booking: new `BookForPatientUseCase.execute(actor_id, patient_id, appointment_type_id, start, room_id | None, clinician_id | None)`: clinician = actor's profile, a different `clinician_id` gives `forbidden`; inactive patient `forbidden` (`refuse_non_patient`); `Placement.place(..., for_patient=False, actor=actor_id, room_id=...)`, source `STAFF`; a named room must be an active room of the department (`not_found` otherwise), then free (`conflict`) | §5.4; Story réserve par l'API; §9 has no screen for it (Epic assumption) |
| `POST /appointments` body gains optional `patient` and `room`: a patient caller naming another patient or a room gets `forbidden`; a clinician caller must name `patient` (`invalid_input` otherwise) | §5.4 « a patient cannot choose a room » |
| `GET /appointments` for a clinician: rows of their own profile only, any `clinician` parameter ignored; filters `patient`, `status`, `from`, `to`; no notes | Story agenda du jour |
| Read side `ClinicianAgenda` (booking outbound, SQL adapter `SqlClinicianAgenda`): `day`, `week`, `detail`, `patients`, `room_day`, `next_free_slot` | light CQRS, one query per page, p95 kept |
| Cancelled and no-show rows appear in the day list with their status and no action; tiles: `appointments` = all but cancelled, `cancelled` apart, `completed`, `no_show`, next free slot | open question E6; §9 « cancelled counted separately » |
| « Prochain créneau libre » = earliest `scheduling_slot.start` of the clinician, any type, at or after `max(now, start of the shown day)`, not held; « — » when none | open question E6; `scheduling_slot` is per clinician and type |
| Calendar: week starts Monday (`Week`), `?week=` previous / this / next; Today and Rooms: `?day=` previous / next / today; an unusable value falls back to today | open question E6; reuse admin `week_start` |
| Rooms timeline occupancy: active appointments (`BOOKED`, `CHECKED_IN`, `COMPLETED`) | open question E6; « active » = not `CANCELLED` or `NO_SHOW` (§3.1) |
| Patients list: last visit = latest `COMPLETED` start before now; next visit = earliest `BOOKED` or `CHECKED_IN` start after now; search `ILIKE` on full name; paged by 20 (`PageRequest`) | open question E6 |
| History = `AuditQueries.entries_for("appointment", id)` in `at` order, shown as action label, actor role and local time; booking reads it through outbound `AppointmentHistory` (`AuditAppointmentHistory` adapter); audit index on `(entity_type, entity_id, at)` | §9; `entity_id` not indexed today |
| UI strings « Not your appointment » and « Occupied » kept verbatim from the Stories in `lang="en"` spans; the rest of the UI stays French | Success Evidence quotes them |
| Allowed actions computed by booking `clinician_actions(appointment) -> frozenset[ClinicianAction]` (check-in, complete, no-show, cancel, reschedule), separate from the patient `allowed_actions` | Story « ne proposent que les actions permises » |
| No Locust run: no change to search or anonymous booking; workspace reads filter on indexed `appointment_clinician_start`, `appointment_room_start` (`booking/infrastructure/django/models.py:56-59`) and the new audit index | p95 constraint proven by the E3 load test |
| Calendar time off comes from scheduling's `AvailabilityQueries.time_offs_of`, not from booking SQL | no new cross-context SQL read |
| History actor = « Patient », « Praticien » or « Personnel » derived from the appointment's own ids | no identity lookup; audit stores only `actor_id` |
