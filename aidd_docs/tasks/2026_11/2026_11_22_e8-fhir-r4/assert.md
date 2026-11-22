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
