# Assert: E8 - Un client FHIR R4 fait tout ce que les écrans permettent, ni plus ni moins
## Round 1
- Head: `7f0ebd4`
- Uncommitted changes: yes
- Verdict: FAIL

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pyrefly check` | 0 | |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | |
| `uv run pytest tests/fhir tests/use_cases/identity tests/contracts/test_api_tokens.py tests/contracts/test_readers.py tests/contracts/test_identity_repositories.py tests/api/test_same_origin.py tests/api/test_domain_errors.py tests/api/test_auth_endpoints.py tests/integration/test_seed.py` | 0 | |
| `uv run pytest tests/use_cases tests/contracts tests/api tests/presenters -q -p no:randomly` | 0 | |
| `uv run pytest tests/test_acceptance_names.py` | 1 | `Un client agit avec le jeton d'un utilisateur et exactement ses droits: bullets without a scenario` (5 bullets, phases 2 to 8) |
| pre-commit hooks of `5f4ddfd` (Python Doctor 90 after fixes) | 0 | |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

## Round 2
- Head: `89ffa47`
- Uncommitted changes: yes
- Verdict: FAIL

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pyrefly check` | 0 | |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | |
| `uv run pytest tests/fhir tests/contracts tests/api tests/use_cases/identity -q` | 0 | |
| `uv run pytest tests/test_acceptance_names.py -q` | 1 | `bullets without a scenario`: token story (4 bullets, phases 4 to 8); « sans jeton » story: `Slot` (phase 3) and « toute écriture renvoie `unauthenticated` » (no write declared before phase 4: an undeclared write answers 405 first) |
| pre-commit hooks of `5f4ddfd` (Python Doctor 90 after fixes) | 0 | |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

## Round 3
- Head: `290bc45`
- Uncommitted changes: yes
- Verdict: FAIL

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pyrefly check` | 0 | |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | |
| `uv run pytest tests/fhir tests/use_cases tests/properties tests/contracts tests/api tests/presenters -q` | 0 | |
| `uv run pytest tests/test_acceptance_names.py -q` | 1 | `bullets without a scenario`: token story (4 bullets, phases 4 to 8); « sans jeton » story: « toute écriture renvoie `unauthenticated` » (no write declared before phase 4); the `Slot` bullets are covered |
| pre-commit hooks of `290bc45` (Python Doctor included) | 0 | |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

## Round 4
- Head: `0af0fda`
- Uncommitted changes: no (plan docs only)
- Verdict: PASS for phase 4 scope

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pyrefly check` | 0 | |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | |
| `uv run pytest tests/fhir tests/use_cases tests/properties tests/contracts tests/api tests/presenters tests/test_acceptance_names.py tests/integration/test_concurrent_conditional_writes_postgres.py -q` | 0 | 1653 passed |
| `test_concurrent_conditional_writes_postgres.py` with the `select_for_update` of `DjangoConditionalWrites` removed | 1 | expected: `second_was_blocked` `[False] == [True]` on both targets |
| pre-commit hooks of `0af0fda` (Python Doctor included) | 0 | |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

- `tests/test_acceptance_names.py` is green: the token story's four bullets and « Sans jeton, toute écriture renvoie `unauthenticated` (401). » (on `PUT Patient`, re-proven for every write in phase 11).
- To record in `architecture.md` (phase 11): `interop/infrastructure/conditional_writes.py` is a second lock adapter locking other contexts' rows by their ORM models (clinician profile, user, appointment, availability rule), the accepted exception beside booking's `schedule_locks`.
- Deviations: the read port is `PatientQueries` (rule 0-ports: several reads make a `*Queries` port), not `PatientReads`; the token scenarios stay in `tests/features/identity/…` run by `tests/use_cases/identity/test_api_tokens.py`; field errors raised by `UpdateProfile` keep their product names (`phone`, `birth_date`) in `expression`, only diff refusals carry FHIR paths; `phase-3.md` still says `status: pending` although round 3 closed it.

## Round 5
- Head: `4e1a432`
- Uncommitted changes: no (plan docs only)
- Verdict: PASS for phase 5 scope

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pyrefly check` | 0 | |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | |
| `uv run pytest tests/fhir tests/contracts tests/use_cases tests/api tests/presenters tests/test_acceptance_names.py -q` | 0 | 1655 passed |
| pre-commit hooks of `4e1a432` (Python Doctor included) | 0 | |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

- Every bullet of « Un client réserve et consulte des RDV en FHIR » names a scenario; each refusal is replayed on `POST /api/v1/appointments` with the same token and answers the same status, code and (but for `invalid_input` field paths) details.
- Deviations: the read port is `InteropAppointmentQueries` (booking already owns an `AppointmentQueries`, rule 0-ports: two reads make a `*Queries` port), not `AppointmentReads`; `comment` is refused on create beside `reasonCode` (no screen writes notes while booking); an inactive patient booked by the admin answers 403 `forbidden`, as `refuse_non_patient` does; a clinician sees no waitlist entry (§15.4, plan decision); a hold carries no patient participant, its visitor has no account.
- To record in `architecture.md` (phase 11): `SqlInteropAppointmentQueries` takes the `Clock` so an expired hold is absent, as in the slot query.

## Round 6
- Head: `953d2cf`
- Uncommitted changes: no (plan docs only)
- Verdict: PASS for phase 6 scope

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 | |
| `uv run ruff format --check .` | 0 | |
| `uv run lint-imports` | 0 | |
| `uv run pyrefly check` | 0 | |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | |
| `uv run pytest tests/fhir tests/contracts tests/use_cases tests/api tests/presenters tests/test_acceptance_names.py -q` | 0 | 1679 passed |
| two mutants (several intentions accepted, cancel reason forced) | 1 | 5 scenarios fail, reverted |
| pre-commit hooks of `953d2cf` (Python Doctor included) | 0 | |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

- Every bullet of « Un client déplace, annule et change le statut d'un RDV en FHIR » names a scenario; refusals are replayed on `POST /api/v1/appointments/{id}/…` with the same token (same status, code and, but for `invalid_input`, details); audit, notifications and emails are compared with the application API, notes with the workspace file screen.
- Deviations: emails are read from the recording outbox of the `bookable` scene, as in phase 5, not from Mailpit; a waitlist entry or a hold answers 409 `invalid_transition` with its own status on any `PUT` (§15.6 updates appointments only; phase 7 accepts offers through `AppointmentResponse`); several intentions in one update answer `invalid_input` naming every changed path; a `cancelationReason` changed without `status` is `invalid_input`; a missing cancellation reason keeps the use case's field name `reason`, as phase 4 kept product names; the « other status » refusal is built in the mapper with the domain's message and `{status}` details, since no use case exists for it.

## Round 7
- Head: `0e4c5d3`
- Uncommitted changes: no (plan docs only)
- Verdict: PASS for phase 7 scope

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 |  |
| `uv run ruff format --check .` | 0 |  |
| `uv run lint-imports` | 0 |  |
| `uv run pyrefly check` | 0 |  |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | no migration: the appointment reuses the entry's UUID, tables keep their own primary keys |
| `uv run pytest tests/fhir tests/contracts tests/use_cases tests/api tests/integration/test_concurrent_waitlist_*_postgres.py tests/test_acceptance_names.py -q` | 0 | 1616 passed |
| `uv run pytest tests/presenters -q` | 0 | 94 passed |
| mutant: `AcceptWaitlistOffer` places without the entry id | 1 | 5 scenarios fail, reverted |
| pre-commit hooks of `0e4c5d3` (Python Doctor included) | 0 |  |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

- Every bullet of « Un patient rejoint la liste d'attente et accepte une offre en FHIR » names a scenario; join and accept refusals are replayed on `POST /api/v1/waitlist` and `/waitlist/{id}/accept` with the same token (same status, code and, but for `invalid_input`, details); audit, notification and emails of a FHIR acceptance are compared with an API one, ids left out.
- Deviations: `JoinWaitlist` gains `patient_id` (FHIR names a `Patient/<id>`), unknown or inactive → `not_found` as by email; the port is `AppointmentResponseQueries` (rule 0-ports), not `AppointmentResponseReads`; `AppointmentResponse.actor` is the server's, ignored on create like `Appointment.end`; only `participantStatus` `accepted` is created; a clinician reads no `AppointmentResponse` (`forbidden`), as the Story names the patient and the admin; search declares `patient` and `appointment`; `requestedPeriod` is written as dates and read back as instants (midnights of the type's zone, the end exclusive); a `conflict` is not replayed on the API, since the entry is back to `WAITING` and would answer `invalid_transition`.
- To record in `architecture.md` (phase 11): an accepted entry and its appointment share one id; `SqlAppointmentResponseQueries` serves `BOOKED` entries.

## Round 8
- Head: `4c0ca45`
- Uncommitted changes: no (plan docs only)
- Verdict: PASS for phase 8 scope

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 |  |
| `uv run ruff format --check .` | 0 |  |
| `uv run lint-imports` | 0 |  |
| `uv run pyrefly check` | 0 |  |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | no migration: both resources read existing tables |
| `uv run pytest tests/fhir tests/contracts tests/use_cases tests/api tests/presenters tests/integration/test_concurrent_conditional_writes_postgres.py tests/test_acceptance_names.py -q` | 0 | 1757 passed |
| mutant: `received` writable once read | 1 | 1 scenario fails, reverted |
| mutant: `admin_only` lets anyone read | 1 | 8 tests fail, reverted |
| pre-commit hooks of `4c0ca45` and `0ad0256` (Python Doctor included) | 0 |  |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

- Every bullet of « Un client lit les notifications de son utilisateur en FHIR » and « L'admin consulte le journal d'audit en FHIR » names a scenario; a reading filled in FHIR shows read on `/portal/notifications` and is audited `notification.read` as there; audit events are compared field by field with `audit_auditentryrecord`, and no person's email or name appears in them.
- Phase 7 leftover (`0ad0256`): a clinician naming a practitioner they cannot resolve gets 403 `forbidden`, not 404; an unseen practitioner reaches `JoinWaitlist` as is, which refuses the caller first, then answers `not_found`.
- Deviations: Communication `If-Match` locks the recipient's user row (`WriteTarget.user`), already raced in `test_concurrent_conditional_writes_postgres.py`, instead of a new notification lock; `received` takes the server's clock, as the portal does, and once filled is no longer writable (`invalid_input`); the admin guard is interop's `admin_only(reader)`, called by both `AuditEventQueries` adapters, so a search is `forbidden`, not empty; `AuditEvent.type` is the action's prefix, `subtype` the action, `source.observer` the display « DrLibre », a visitor or job agent is named « système » with `requestor` false, an unserved entity type (`session`, `time_off`, `api_token`) or a deleted user is an `identifier`; `entity` search takes any served `<Type>/<id>`, `entity-type` the product type; the `date` bounds helper moved from the Appointment router to `routing.instants`, shared with `sent`.
- To record in `architecture.md` (phase 11): `Communication` and `AuditEvent` are read by interop SQL; only the admin reads `AuditEvent`.

## Round 9
- Head: `a0fa036`
- Uncommitted changes: no (plan docs only)
- Verdict: PASS for phase 9 scope

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 |  |
| `uv run ruff format --check .` | 0 |  |
| `uv run lint-imports` | 0 |  |
| `uv run pyrefly check` | 0 |  |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | no migration: writes reuse the console's tables |
| `uv run pytest tests/fhir tests/contracts tests/use_cases tests/api tests/presenters tests/integration/test_concurrent_conditional_writes_postgres.py tests/test_acceptance_names.py -q` | 0 | 1803 passed |
| race test per reference target (hospital, department, room, appointment type, specialty) with the row lock removed | 1 | 5 tests fail, reverted |
| mutant: `require_admin` lets anyone write | 1 | 7 scenarios fail, reverted |
| mutant: the hospital description is dropped on write | 1 | 2 scenarios fail, reverted |
| pre-commit hooks of `a0fa036` (Python Doctor 90 after removing a literal empty password) | 0 |  |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

- Every bullet of « L'admin gère le référentiel en FHIR » names a scenario; each write's audit trail (create, rename, delete) is compared entry by entry with the console doing the same, actor and metadata included, ids blanked; every element a client sends is read back, so an update from the read loses nothing.
- Lock order: no organisation use case nor `SaveUser` takes a row lock (`records.py`, `save_user.py`; `RefreshSlots` takes none), so `If-Match` locks the record's own row (`WriteTarget.record`, new `Locked` members); `PractitionerRole` locks the profile as `lock_profile`, `Practitioner` and `Patient` the user row.
- Deviations: the `ValueSet` stays read-only (POST, PUT, DELETE answer 405) and follows the `CodeSystem` writes, against the bullet « l'admin … `ValueSet` », to record in the PR and `open-questions.md`; writes are served by `routers/reference_writes.py` on the directory router (Ninja needs one router per path); `Organization` gains a `description` extension so a hospital or department round-trips; the profile's title is the write-only `title` extension of `PractitionerRole`, kept when absent, read on `Practitioner.name.prefix`; a staff user's role is the write-only `role` extension of `Practitioner` (`clinician` by default on create, kept when absent), so an admin is also created and their own role change refused there; an admin's `PractitionerRole` (id = user) is not writable (`invalid_input`, write the `Practitioner`); a site `Location` write is `invalid_input` « Le site s'écrit par son Organization `prov` »; admin updates refuse a changed phone or title (`invalid_input`), a patient's phone or birth date and a role's `availableTime` or `notAvailable` (`forbidden`, other role); computed elements (site `partOf`, type specialties, role services, department `active`) are ignored; deletes answer 204 without `If-Match`.
- To record in `architecture.md` (phase 11): reference writes go through the console's use cases with `require_admin` at the FHIR door; `If-Match` on a reference record locks its own row.

## Round 10
- Head: `5741f30`
- Uncommitted changes: yes (phase 10, committed as `7fe2e1b`, its pre-commit hooks all pass)
- Verdict: PASS for phase 10 scope

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 |  |
| `uv run ruff format --check .` | 0 |  |
| `uv run lint-imports` | 0 |  |
| `uv run pyrefly check` | 0 |  |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | no migration |
| `uv run pytest tests/fhir tests/contracts tests/use_cases tests/api tests/presenters tests/integration/test_concurrent_conditional_writes_postgres.py tests/test_acceptance_names.py -q` | 0 | 1834 passed |
| mutant: the notAvailable write without `all_or_nothing` | 1 | 1 scenario fails (« une période refusée, aucune écrite »), reverted |
| mutant: a clinician may write another's role | 1 | 1 scenario fails, reverted |
| mutant: a schedule may name another practitioner | 1 | 3 scenarios fail, reverted |
| mutant: a clinician's role diff dropped | 1 | 4 scenarios fail, reverted |
| `uv run pytest -m e2e`, full suite | not run | out of scope: once at the end of the plan |

- Every bullet of « Le praticien gère ses disponibilités en FHIR » names a scenario; each `Schedule` and `notAvailable` write's audit trail is compared entry by entry with the workspace screens (`/workspace/availability/`, `/workspace/time-off/`), actor and metadata included; `Slot` searches show each change at once; a booked appointment inside a new time off stays `BOOKED`.
- All or nothing: `ConditionalWrites.run(all_or_nothing=True)` opens the outer transaction with or without `If-Match`, locks the target and lets a refusal roll back every use case already run; the default keeps the waitlist's commit-then-raise; the fake only runs the write, so the rollback is proven on PostgreSQL (`test_an_all_or_nothing_refusal_keeps_none_of_the_writes_before_it`) and by the scenario.
- Deviations: `Schedule` actors are matched to the token holder at the door (`_named_self`: a schedule naming another practitioner, created or updated, is `forbidden` before any diff), `DeleteAvailabilityRule` judges deletes; `Schedule.id`, `meta`, `active` and `planningHorizon` are optional on write, `active` is computed and ignored, a horizon sent on create or changed on update is `invalid_input` (`Schedule.planningHorizon`); `valueTime` `HH:MM:00` maps to the screen's `HH:MM`; `notAvailable` periods match one for one on start, end (instants, any offset) and description, removals run before additions, a description « Indisponible » means no reason, an instant without offset is `invalid_input`; local times are read in the role's hospital zone; a clinician's `PUT PractitionerRole` changing anything but `notAvailable` is `forbidden`, another clinician's role or a patient is `forbidden`.
- To record in `architecture.md` (phase 11): `Schedule` and `notAvailable` writes go through the workspace's use cases, `If-Match` locking the profile then the rule; `ConditionalWrites` `all_or_nothing` makes a multi-call write atomic.

## Round 11
- Head: `ad7dc3a`
- Uncommitted changes: no (plan docs only)
- Verdict: PASS for phase 11 and the plan

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run ruff check .` | 0 |  |
| `uv run ruff format --check .` | 0 |  |
| `uv run lint-imports` | 0 | 12 kept, 0 broken |
| `uv run pyrefly check` | 0 |  |
| `uv run python manage.py makemigrations --check --dry-run` | 0 | no migration |
| `uv run pre-commit run --all-files` | 0 | Python Doctor 90 after `# nosec B311` on the new Locust task |
| `docker compose up -d --build` then `uv run pytest` | 0 | 2108 passed, 11 deselected |
| `uv run pytest -m e2e` | 0 | 11 passed |
| `curl -i localhost:8000/fhir/metadata` | 0 | 200, `application/fhir+json; charset=utf-8`, `x-correlation-id` |
| `./scripts/load-run.sh` | 0 | FHIR `Slot` search p95 88 ms, 0 failures (`load-results.md`) |
| mutant: Communication search ignores `category` | 1 | « paramètres, `_include` et `_sort` déclarés » fails, reverted |
| mutant: Slot search ignores `_sort=-start` | 1 | same scenario fails, reverted |

- Every bullet of « Un client découvre les capacités du serveur dans le CapabilityStatement » names a scenario; « déclaré = servi » is proven four ways: Ninja routes equal the registry's, each undeclared interaction answers 405 with `Allow` the declared methods, each search reads every declared parameter, `_include` and `_sort` (watched `SearchQuery.values` and `_listed`), each search refuses an undeclared parameter, `_include` or `_sort`.
- Epic Success Evidence (`tests/fhir/test_parcours_fhir_de_l_epic.py`, demo seed in the test database, fixed tokens): a visitor's free `Slot` booked with `demo-patient-token` (`booked`, practitioner and room) then cancelled leaves the same audit entries (action, type, metadata, actor) and notifications as the booking screen and portal cancel; that token gets 403 on another patient's appointments and `Patient`, and searches leave them out; each of the 28 declared writes maps to a scenario refusing it as the screen or API does; « Sans jeton, toute écriture renvoie `unauthenticated` (401). (chaque écriture déclarée) » sends all 28.
- Added refusal rows: 12 reference writes and `PUT Patient` refused `forbidden` to non-admins, as the console's `require_role`.
- Deviations: `metadata.py` needed no change (already read from the registry); `tests/fhir/test_metadata.py` folded into the Story's test; the Epic journey runs in-process on the seed rather than over HTTP against compose, so audit and notifications are read from the same database.

## Round 12
- Head: `51330fd` plus the `ValueSet` fix
- Uncommitted changes: yes (the fix, before its commit)
- Verdict: PASS; closes the validation's failed bullet « L'admin seul crée, modifie et supprime … `ValueSet` … »

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pytest tests/fhir tests/contracts tests/test_acceptance_names.py` | 0 | 754 passed |
| `uv run ruff check .` | 0 |  |
| `uv run ruff format --check .` | 0 |  |
| `uv run lint-imports` | 0 | 12 kept, 0 broken |
| `uv run pyrefly check` | 0 | 0 errors |
| `uv run pre-commit run --all-files` | 0 |  |
| `uv run pytest` | 0 | 2114 passed, 11 deselected |

- A specialty is a `CodeSystem` and a `ValueSet` sharing its product id; the admin creates, renames, deletes `ValueSet` through `SaveSpecialty`/`DeleteSpecialty`, `If-Match` on `Locked.SPECIALTY`, others get `forbidden`; read and search (`name`, `status`) for anyone, active only unless admin.
- The aggregate `ValueSet/specialties` is gone (§15.1 product ids); the deviation scenario is replaced by Examples rows (create, rename, delete, three refusals, stale `If-Match`, audit equal to the console's) and a scenario reading one specialty as both resources.
- Declared writes go from 28 to 31; `SAME_REFUSAL`, the 401 scenario and the CapabilityStatement test derive from the registry and pass.

## Round 13
- Head: `3fbc12f` plus the review round 1 fixes
- Uncommitted changes: yes (the fixes, before their commits)
- Verdict: PASS; closes review round 1 findings bearer scope, time-off reasons, `UpdateProfile` actor, `ConditionalWrites` refusal, FHIR prefix literal

| Check | Exit | Failure |
| --- | --- | --- |
| `uv run pytest tests/fhir tests/contracts/test_interop_directory.py tests/contracts/test_conditional_writes.py` | 0 | 311 passed |
| `uv run pytest tests/integration/test_concurrent_conditional_writes_postgres.py` | 0 | 8 passed; without the row locks 7 failed |
| `uv run ruff check .` | 0 |  |
| `uv run ruff format --check .` | 0 |  |
| `uv run lint-imports` | 0 | 12 kept, 0 broken |
| `uv run pyrefly check` | 0 | 0 errors |
| `uv run pre-commit run --all-files` | 0 |  |
| `uv run pytest` | 0 | 2121 passed, 11 deselected |

- A bearer authenticates only under `/fhir/` and `/api/` (`interfaces/paths.py`); on `/console/` and the CSV export its holder is anonymous (redirect to sign-in); `/api/v1/appointments` still answers 200; the tests fail with the guard removed.
- Time-off reasons reach only the admin and the owning clinician (`Reader.reads_reasons_of`), SQL and fake alike; others read « Indisponible ».
- `UpdateProfile.execute(actor_id=…)` refuses another user `forbidden`; the FHIR router's own check is gone; scenario « Règle §15.4 : seul le patient modifie son propre téléphone et sa date de naissance ».
- `ConditionalWrites.run` always writes inside its outer transaction, `all_or_nothing` removed; no caller commits then raises (the waitlist accept doesn't go through it); row locks are `FOR NO KEY UPDATE`, race tests still pass with the lock and fail without.
