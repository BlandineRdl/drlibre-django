# Review: E8 FHIR R4
## Round 1
- Diff: `main...3fbc12f`
- Uncommitted changes: yes (`CLAUDE.md`, out of scope)
- Axes: code, relevancy
- Verdict: changes-requested, because of three major findings (bearer scope, time-off reasons, a role guard held only by the router)

### Criteria
- Functional axis not run; acceptance evidence is the caller's (suite, e2e, validator).

### Assumptions
- Cookie ignored under `/fhir/`, so the SameOrigin exemption opens no CSRF surface — holds, `src/drlibre/interfaces/web/auth.py:52`, `config/middleware.py:56`
- Tokens are stored hashed, expiry and the user's `active` flag are checked on every request — holds, `src/drlibre/identity/application/use_cases/api_tokens.py:100-105`
- Interop SQL binds every value — holds; only fixed fragments are formatted (`sql_directory.py:159,373,410`)
- Appointment PUT locks clinician, patient, then the appointment row, in booking's order — holds, `src/drlibre/interop/application/ports/inbound.py:231-236`
- Clinical notes go only to the appointment's clinician — holds, `sql_appointments.py:28`
- Holds are shown to staff only, without an email — holds, `sql_appointments.py:41-45,56`

### Findings
- `src/drlibre/interfaces/web/auth.py:68-70` : the bearer token authenticates every path, so a 90-day token also opens the web console (CSV export included) and `/api/v1`. Spec §2 limits the token to the FHIR API, and the memory says "Under `/fhir/` only the bearer counts". Proof: `drlibre-specs.md:30`, `architecture.md:90`. Fix: read the bearer only when `request.path.startswith(FHIR_PREFIX)`. Plan line 74 records the opposite choice, so the spec and the plan need settling — 🟡 major
- `src/drlibre/interop/infrastructure/sql_directory.py:258` : time-off reasons are shown to every staff reader, so any clinician reads a colleague's reasons through `PractitionerRole.notAvailable.description` (`mappers/directory.py:292`). No screen shows them to anyone but the owning clinician (`presenters/availability.py:114`), and a reason can be health data. Fix: keep `reason` only when `reader.is_admin` or `reader.profile_id == row id` — 🟡 major
- `src/drlibre/interfaces/fhir/routers/patients.py:156-166` : the router alone decides "the patient themself or an admin". `UpdateProfile.execute(user_id=…)` takes no actor (`identity/application/ports/inbound.py:190`), so nothing below the router guards it, which breaks rule `0-interfaces-no-business-rule` ("never decide a role in a router"). The same holds for `reference_writes.py:570,616` (own role, own schedule). Fix: pass `actor` to `UpdateProfile` and refuse a different user in the use case, then drop the router check — 🟡 major
- `src/drlibre/interop/infrastructure/conditional_writes.py:61-66` : the "refusal after its own commit" branch serves no caller. The only write that commits and then raises (accepting an offer) does not go through `ConditionalWrites` (`routers/appointment_responses.py:123`). The branch also makes the default mode commit a partial multi-step write. Fix: `return write()` inside the `atomic`, which makes `all_or_nothing` the only mode and lets the flag go — 🟢 minor
- `src/drlibre/interfaces/fhir/routers/communications.py:140-141` : "once read, stays read" is decided in the router. Fix: let `MarkNotificationRead` refuse un-reading, or keep it as pure FHIR mapping and name it so — 🟢 minor
- `config/middleware.py:56` : the `"/fhir/"` literal repeats `FHIR_PREFIX` (`web/auth.py:20`). Fix: import the constant — 🟢 minor
- `scripts/seed_showcase.py` : 648 lines of demo seed (commit `2f6d3fb`) that the E8 Epic does not ask for. Fix: ship it in its own PR — 🟢 minor

### Limits
- `DjangoConditionalWrites` takes `FOR UPDATE`, which also blocks inserts' `FOR KEY SHARE` on that row. For example, an admin `If-Match` update of an `AppointmentType` stalls bookings of that type until it commits. No deadlock found (`RefreshSlots` takes no profile lock). A two-writer test would settle it; `select_for_update(no_key=True)` would avoid the stall.
- Reactivating a user brings back their unexpired tokens (`save_user.py:69` closes sessions only). The spec doesn't say whether that is intended.
- An unbounded `Slot` search computes every state in memory before paging (`routers/slots.py:182`). `FindFreeSlots` caps it at 31 days, and `load-results.md` was not re-checked.

## Round 2
### Findings
- `src/drlibre/interop/infrastructure/conditional_writes.py:50` : `FOR NO KEY UPDATE` was upgraded to `FOR UPDATE` mid-write when the use case re-locked the profile (`scheduling/infrastructure/repositories.py:35`) or the user (`booking/infrastructure/schedule_locks.py:21-35`), a lock-upgrade deadlock risk — fixed: profile and user rows take `FOR UPDATE`, rows no use case re-locks (appointment, rule, reference records) keep `FOR NO KEY UPDATE`; race tests pass with the locks, 7 of 8 fail without — 🟡 major
- `config/middleware.py:75` : the `"/api/"` literal repeats `API_PREFIX` — fixed, imported from `drlibre.interfaces.paths` — 🟢 minor
- `src/drlibre/interfaces/fhir/routers/patients.py:159-166` : a clinician's PUT on their own patient with a stale `If-Match` answered 412 instead of 403 — fixed: a non-owner non-admin is refused `forbidden` before the version and the fields, from the reader's scope like `_visible`; `UpdateProfile` still refuses; scenario « pas le praticien, même avec un `If-Match` périmé » — 🟢 minor

### Decisions
- `communications.py` once-read rule stays in the router: it maps FHIR field mutability, not a business rule.
- `reference_writes.py` own-role and own-schedule guards are URL/actor consistency checks; the use cases derive the profile from the actor.
- `scripts/seed_showcase.py` comes from the pre-existing user commit `2f6d3fb` (also on `feat/ui-polish`), out of E8 scope; flagged in the PR.
- Spec §2 line 30 limits tokens to FHIR, `INSTALL.md:17` says API/FHIR: API and FHIR kept, spec wording unchanged.
