# Review: E4 - Le patient gère ses rendez-vous et reste informé
## Round 1
- Diff: `main...9819088`
- Uncommitted changes: no
- Axes: code, relevancy
- Verdict: changes-requested, because two major findings: the reschedule page offers slots and an action the rules then refuse

### Criteria
- Out of the diff: functional axis not run (validator PASS reported by the caller, 36 Story bullets)

### Assumptions
- Reschedule ignores its own appointment in conflicts, rooms and free slots — holds, checked at `src/drlibre/booking/application/use_cases/reschedule_appointment.py:61`, `:70`, `:84` and `src/drlibre/scheduling/application/use_cases/computed_slots.py:49`
- Recomputing slots on a sub-window yields the same grid as the stored table — holds, rule-anchored grid at `src/drlibre/scheduling/domain/slot_engine.py:37`, busy extended after end only at `src/drlibre/scheduling/domain/slot.py:24`
- Lock order email, clinician, patient, rooms; re-read under locks — holds, `reschedule_appointment.py:50-55`, `cancel_appointment.py:39-43`, rooms in `placement.py:226`
- Reminder sent once — holds, partial unique index plus savepoint, `src/drlibre/notifications/infrastructure/repositories.py:38`; email only on insert, `src/drlibre/booking/infrastructure/outbox_notices.py:51`
- A reminded appointment cannot be moved, so the unique reminder never goes stale — holds, both happen inside 24 h, `booking_rules.py:46`
- Ownership — holds, `own_appointment` in each use case, `MarkNotificationReadUseCase` checks recipient, list guarded by `refuse_non_patient`
- Notifications and audit hold no personal data — holds, `notification.py` body is time and zone only; audit metadata ids, kinds, field names
- python-doctor on the git index — holds: `pass_filenames: false`, trap cleans the temp tree, index equals the work tree under pre-commit's stash

### Findings
- `src/drlibre/scheduling/application/use_cases/find_free_week.py:34` : the reschedule week lists slots starting within 120 min (stored and computed slots are cut at `now`, `open_slots.py:27`), which `reschedule_violations` then refuses as `lead_time_too_short`, proof `src/drlibre/booking/domain/booking_rules.py:65`; search already starts at now + lead time (`search/domain/horizon.py`) → start the week at `max(window.start, now + BOOKING_LEAD_TIME)` — 🟡 major
- `src/drlibre/booking/domain/booking_rules.py:80` : « Déplacer » is offered for an appointment whose type is not bookable online (a `STAFF` booking), every move then refused `type_not_bookable_online`, proof `booking_rules.py:66-67` and Story « proposée que quand les règles la permettent » → carry the type's `bookable_online` in `AgendaEntry` and require it in `allowed_actions` — 🟡 major
- `src/drlibre/scheduling/domain/week.py:25` : duplicates the week clamp and neighbours of `src/drlibre/search/application/use_cases/view_provider_page.py:26-42` (`monday_of`, first/last horizon Monday, previous/next) → one `Week` in `shared_kernel`, used by both — 🟢 minor
- `src/drlibre/interfaces/web/views/portal.py:60` : `next(...)` without default raises `StopIteration`, a 500, if the agenda join drops a row `view_appointment` found → `next(..., None)` then `not_found` — 🟢 minor
- `src/drlibre/identity/application/use_cases/update_profile.py:21` : « not after today » uses the UTC date; between local midnight and 01:00/02:00 Paris, today's birth date is refused → compare in `settings.TIME_ZONE`'s date (pass the zone or a local date) — 🟢 minor
- `src/drlibre/interfaces/web/views/portal.py:36` : catches `rule_violation`, `invalid_transition`, `conflict`, `no_room_available` against rule 6-domain-errors and `architecture.md` (only `invalid_input`, `has_dependents`, `forbidden`); precedent `views/booking.py:152` → amend the rule and architecture line to list inline booking refusals — 🟢 minor
- `tests/use_cases/booking/conftest.py` : 1220 lines of steps for nine Stories in one file → split steps per Story module, shared ones kept in conftest — 🟢 minor

### Limits
- Migration 0002 adds exclusion constraints over existing rows; the load seed's hourly starts avoid overlaps, but a hand-made overlapping active pair in an old volume would fail the migration — a migrate on a copied E3 volume would settle it
- Notifications page shows `created_at` in `settings.TIME_ZONE` while bodies use the hospital zone — equal for the demo data; a non-Paris hospital would show both
- `FindFreeWeek` as a scheduling use case is thin but keeps week policy out of the view; not judged over-engineering

## Round 2
- Diff: `9819088...3ecbee2`
- Uncommitted changes: no
- Axes: code, relevancy
- Verdict: changes-requested, because the lead-time fix makes the reschedule page fail on Sunday from 22:00 local

### Criteria
- [x] Week strip starts at now + 120 min — `find_free_week.py:37`, `tests/api/test_portal_pages.py:133` passes
- [x] « Déplacer » only for a type bookable online — `booking_rules.py:85`, `patient_agenda.py:15`, contract `tests/contracts/test_patient_agenda.py:126` (fake and SQL), page scenario `le_patient_deplace_un_rendez_vous.feature:136` (exact action set, `conftest.py:1206`)
- [x] Unlisted appointment → `not_found` — `views/portal.py:60-63`, scenario `feature:141` answers 404
- [x] Birth date « today » in `settings.TIME_ZONE` — `update_profile.py:27`, scenario `le_patient_met_a_jour_son_profil.feature:26`
- [x] Rule 6-domain-errors and `architecture.md` list inline booking refusals — both rule copies and memory amended
- Run: targeted 83 passed; `uv run pytest -q` 941 passed, 8 deselected
- Out of the diff: week dedupe, conftest split (deferred)

### Assumptions
- `FindFreeWeek` serves only the reschedule strip — holds, sole caller `views/portal.py:133`
- `allowed_actions` has one caller, so the keyword-only `type_online` breaks none — holds, `list_patient_appointments.py:32`
- `Period` accepts `start >= end` — finding, it raises `invalid_input` at `scheduling/domain/slot.py:15`

### Findings
- `src/drlibre/scheduling/application/use_cases/find_free_week.py:37` : when `now + 120 min >= window.end` (current week, Sunday 22:00–24:00 in the type's zone), `FindFreeSlots` builds `Period(start, end)` with `end <= start` and raises `invalid_input`, proof `scheduling/domain/slot.py:15` and `find_free_slots.py:46`; the week is reached by default (appointment in the current week) or by « ‹ Semaine précédente » (`week.py:35`), and `views/portal.py:133` calls it outside the `try`, so GET and POST both end on an error page → return the week with no slots when `start >= window.end`, plus one test at Sunday 22:30 Paris — 🟡 major
- `src/drlibre/booking/application/use_cases/create_hold.py:94` : the booking hold still checks the birth date against the UTC date, the same rule the profile now checks in local time; between local midnight and 01:00/02:00 a visitor born today is refused while the profile accepts it → pass the zone as in `UpdateProfileUseCase` — 🟢 minor (outside the diff, incoherence the fix creates)
- `tests/use_cases/booking/conftest.py:1182` : « the agenda no longer lists the appointment » swaps the fake's `appointments`, a state no real adapter reaches (same table); the scenario guards a defensive branch only → acceptable, or drop scenario and branch together if the join cannot lose a row — 🟢 minor

### Limits
- Whether `SqlPatientAgenda` can drop a row `view_appointment` finds (inner joins on clinician, user, type, hospital, department) — FK constraints on those columns would settle it; if all are non-null FKs the new `not_found` branch is dead code
