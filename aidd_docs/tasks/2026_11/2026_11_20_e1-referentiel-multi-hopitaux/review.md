# Review: E1 - Le personnel se connecte et gère le référentiel multi-hôpitaux
- Rounds: 1
- Started: 2026-11-20

## Round 1 · r-dfeb
- Date: 2026-11-20
- By: Black Sun
- Diff: `main...c296fc9`
- Axes: code, functional, relevancy
- Verdict: changes-requested
- Score: 17/18 met, 1 unmet, 0 unverified at runtime, 0 out of the diff

### Criteria
- [x] P1.1 `uv sync --locked` and `check --deploy` pass — `uv lock --check` resolved; pre-commit `django check --deploy` Passed
- [x] P1.2 audit contract green on fake and PostgreSQL; failing audit rolls back the write — tests/contracts/test_audit_log.py, tests/integration/test_unit_of_work_postgres.py:25
- [x] P1.3 cross-origin POST → 403; same-origin and no-Origin pass — tests/api/test_same_origin.py:7-24; curl with `Origin: https://evil.example` → 403
- [x] P1.4 unknown page renders the 404 in the layout — tests/api/test_same_origin.py:32
- [x] P2.1 domain reached through use-case scenarios only — tests/use_cases/identity/test_identity.py
- [x] P2.2 sign_in and lockout features green; contracts on PostgreSQL and Redis — tests/features/identity/sign_in.feature, lockout.feature, tests/contracts/test_failed_sign_ins.py; `uv run pytest` 240 passed
- [x] P2.3 access.feature green; redirect, 403 and role homes — tests/api/test_auth_endpoints.py:21,60,67
- [x] P2.4 change_password.feature green, forced change enforced — tests/features/identity/change_password.feature:27, tests/api/test_auth_endpoints.py:124
- [x] P3.1 invalid values refused with field messages — hospitals.feature:10, appointment_types.feature:14, rooms.feature:14
- [x] P3.2 deletion refusals green; failing audit leaves no record — refusals split across the entity features (no `deletion_refusals.feature`), hospitals.feature:56
- [x] P3.3 25 rows → pages of 20 and 5, total 25, search narrows — tests/integration/test_reference_queries_postgres.py:23,34
- [ ] P3.4 admin creates and edits each entity through the client; clinician 403 — only the hospital is edited (tests/api/test_console_reference.py:93); department, room, specialty and type edits have no client or BDD test
- [x] P4.1 manage_users.feature green; deactivated session rejected in integration — tests/api/test_console_users.py:45
- [x] P4.2 clinician_profiles.feature and clinician refusals green — clinician_profiles.feature:41-56
- [x] P4.3 admin client attaches a profile; lint-imports green — tests/api/test_console_users.py:77; `Contracts: 6 kept, 0 broken`
- [x] P5.1 seed reruns without duplicates — tests/integration/test_seed.py:19
- [x] P5.2 `pytest -m e2e` green against localhost:8000 — rerun: `3 passed, 240 deselected`
- [x] P5.3 docs name contexts and commands; pre-commit green — aidd_docs/memory/codebase-map.md, coding-assertions.md; pre-commit 8/8 Passed

### Findings
- `src/drlibre/identity/application/use_cases/delete_user.py:52` : deleting a clinician who never acted leaves their clinician profile orphaned; it then blocks deletion of its department, specialty and default room forever, and no screen can remove a profile → add a profile dependent read through an identity outbound port (adapter calls organisation's inbound query) and refuse with `has_dependents` — 🟡 major, fit
- `tests/features/organisation/departments.feature:29` : scenario "Modification et suppression avec confirmation" tests deletion only, no modification; same in rooms.feature:31, specialties.feature:22, appointment_types.feature:39 → add an edit step and its observable outcome, or split into a modification scenario — 🟡 major, fit
- `tests/features/organisation/clinician_profiles.feature:18` : Scenario Outline names embed technical labels through `<field>` (`default_room_id`, `specialty_id`, `weight`); also hospitals.feature:10 (`time_zone`, `latitude`), appointment_types.feature:14 → name examples with user words (`salle par défaut`, `fuseau horaire`) and keep field ids in steps — 🟡 major, conform
- `tests/features/identity/sign_in.feature:54` : scenarios whose names match no Acceptance bullet (sign_in.feature:54,60; access.feature:39,43; lockout.feature:21; rooms.feature:39,45; appointment_types.feature:28,47; hospitals.feature:25; departments.feature:9,13,17) → rename to the bullet they prove, or fold into the bullet's scenario — 🟢 minor, conform
- `src/drlibre/identity/application/access.py:1` : `authorize_owned` is called only from tests; Story bullet "absent → not_found, autre → forbidden" is proven on a guard no route uses → keep as declared groundwork but state in the Story it is unexercised in E1 — 🟢 minor, rot
- `src/drlibre/interfaces/web/views/console_users.py:142` : web views catch `DomainError` (also `forbidden` here), against rule 6-domain-errors; aidd_docs/memory/architecture.md lists only `invalid_input` and `has_dependents` → scope the rule to the API or record the web exception in it, and align architecture.md — 🟢 minor, conform
- `src/drlibre/organisation/application/use_cases/records.py:339` : dependents checked before the unit of work opens; a concurrent child insert turns the delete into a `ProtectedError` 500 → run the check inside `with self._uow` (also delete_user.py:52) — 🟢 minor, error-handling
- `tests/contracts/test_identity_repositories.py:1` : no contract suite for `TokenGenerator` and `UnitOfWork` (fake vs real), against rule 5-fakes-and-contracts → add both — 🟢 minor, conform
- `src/drlibre/audit/domain/audit_entry.py:12` : `_TOKEN` accepts any single word, so a first name passes the personal-data guard → accept strings only for an allow-listed set of keys, or reject strings outside field names/statuses/domains — 🟢 minor, security
- `src/drlibre/organisation/infrastructure/queries.py:107` : clinician list searches title only, not the clinician's name → search on the name via the staff lookup — 🟢 minor, fit
- `scripts/seed.py:123` : seed writes audit entries with an empty actor, which spec §3.1 reserves for failed logins and pre-verification steps → seed as the demo admin once created, or document the exception — 🟢 minor, conform
