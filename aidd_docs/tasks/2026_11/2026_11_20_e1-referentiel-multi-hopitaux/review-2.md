# Review: E1 - Le personnel se connecte et gère le référentiel multi-hôpitaux
- Rounds: 3
- Started: 2026-11-20

## Round 2 · r-b7e2
- Date: 2026-11-20
- By: Black Sun
- Diff: `main...d1c6a60`
- Axes: code, functional, relevancy
- Verdict: changes-requested
- Score: 18/18 met, 0 unmet, 0 unverified at runtime, 0 out of the diff

### Criteria
- [x] P1.1 `uv sync --locked` and `check --deploy` pass — pre-commit this round: `django check --deploy....Passed`, 8/8 hooks Passed
- [x] P1.2 audit contract green on fake and PostgreSQL; failing audit rolls back the write — tests/contracts/test_audit_log.py, tests/contracts/test_unit_of_work.py:59 (new, fake and real); `uv run pytest` 268 passed
- [x] P1.3 cross-origin POST → 403; same-origin and no-Origin pass — tests/api/test_same_origin.py, access.feature:47
- [x] P1.4 unknown page renders the 404 in the layout — tests/api/test_same_origin.py
- [x] P2.1 domain reached through use-case scenarios only — tests/use_cases/identity/
- [x] P2.2 sign_in and lockout features green; contracts on PostgreSQL and Redis — sign_in.feature, lockout.feature, tests/contracts/test_failed_sign_ins.py; 268 passed
- [x] P2.3 access.feature green; redirect, 403 and role homes — access.feature:11,21; tests/api/test_auth_endpoints.py
- [x] P2.4 change_password.feature green, forced change enforced — change_password.feature:27
- [x] P3.1 invalid values refused with field messages — hospitals.feature:10, appointment_types.feature:14, rooms.feature:14
- [x] P3.2 deletion refusals green; failing audit leaves no record — departments.feature:43, rooms.feature:45,55, hospitals.feature:56
- [x] P3.3 25 rows → pages of 20 and 5, total 25, search narrows — tests/integration/test_reference_queries_postgres.py:23,34
- [x] P3.4 admin creates and edits each entity through the client; clinician 403 — tests/api/test_console_reference.py:205 (specialty, department, room, type edits), :94 (hospital), :165 (clinician 403)
- [x] P4.1 manage_users.feature green; deactivated session rejected in integration — tests/api/test_console_users.py:47
- [x] P4.2 clinician_profiles.feature and clinician refusals green — clinician_profiles.feature:41-56,71,77
- [x] P4.3 admin client attaches a profile; lint-imports green — tests/api/test_console_users.py:79; `Contracts: 6 kept, 0 broken.`
- [x] P5.1 seed reruns without duplicates — tests/integration/test_seed.py:21, now also asserts the demo admin as actor
- [x] P5.2 `pytest -m e2e` green against localhost:8000 — rerun: `3 passed, 268 deselected`
- [x] P5.3 docs name contexts and commands; pre-commit green — aidd_docs/memory/architecture.md, codebase-map.md updated; pre-commit 8/8 Passed

### Findings
- `tests/features/identity/sign_in.feature:12` : Outline name `(<role>)` renders `ADMIN`, `CLINICIAN`, `PATIENT` enum codes in scenario names; access.feature:11,21 `(<page>)` and :47 `(<path>)` render URLs such as `/api/v1/auth/login`, against the user rule "no technical labels" (same rule as round 1 finding 3, whose fix covered only the sites it named) → add a `case` column in user words (« admin », « praticien », « patient avec mot de passe »; « console admin », « portail », « connexion par l'API ») and name the outline on it, keeping roles and paths in steps — 🟡 major, conform
- `tests/features/organisation/clinician_profiles.feature:31` : « Le profil se rattache à un utilisateur praticien actif qui n'en a pas » matches no Acceptance bullet and has no « Règle §x : » prefix; same for manage_users.feature:26 « Le mot de passe temporaire respecte la règle de 10 à 72 caractères », and manage_users.feature:17 appends « avec un mot de passe temporaire à changer » to the bullet wording → prefix with « Règle §10 : » (spec §10 Clinicians and Users) or fold into the bullet's scenario — 🟡 major, conform
- `tests/features/identity/manage_users.feature:76` : « Règle §3.2 » is cited for "a clinician with a profile cannot be deleted" and (:82) "cannot change role"; §3.2 states neither, and the §10 User deletion table does not list a profile. The rule is a derived invariant that also narrows the Story bullet « le rôle ... sont modifiables »; also tests/api/test_console_users.py:140 → record the decision (plan Decisions or the Story) and cite it, or cite §3.2 + §10 as derived — 🟢 minor, conform
- `tests/features/organisation/rooms.feature:45` : the name claims « rendez-vous ou des règles de disponibilité », the test covers only an availability rule; appointment_types.feature:60 claims « ou des inscriptions en liste d'attente », tests only an appointment → add the missing case as an Examples row, or narrow the qualifier — 🟢 minor, fit
- `tests/features/organisation/rooms.feature:24` : the scenario name carries « pagination par 20 », but 20 rows out of 20 shows no second page → use 21+ rows and assert page 2, as departments.feature:18 does — 🟢 minor, fit
- `src/drlibre/organisation/infrastructure/repositories.py:47` : the `ProtectedError` → `has_dependents` fallback has no test, and its `{"dependents": []}` lists nothing, while spec §4 says the refusal "lists what still uses the record" → test it on PostgreSQL and list the protected objects from `error.protected_objects`, or document the empty list as the concurrency case — 🟢 minor, error-handling
- `src/drlibre/organisation/application/use_cases/records.py:83` : the comment says the refusal and the delete "see the same rows", which READ COMMITTED does not guarantee without a lock (the fallback above exists because of it); also delete_user.py:51 and delete_clinician_profile.py:32, where a concurrent profile attach can still orphan a profile, since no FK ties profile to user → reword to "narrows the window", or lock the parent row with `select_for_update` — 🟢 minor, code-health
- `tests/contracts/test_clinician_profiles.py:89` : the new outbound method `ClinicianProfiles.delete` is asserted on neither the fake nor the real adapter, against rule 5-fakes-and-contracts → add a contract test that a deleted profile is no longer found — 🟢 minor, conform
- `scripts/seed.py:175` : the first seeded account (the demo admin) is still audited with an empty actor, outside the §3.1 empty-actor cases; the comment documents it and no actor can exist yet → keep, and name it in the PR as an accepted exception — 🟢 minor, conform

## Round 3 · r-4c91
- Date: 2026-11-20
- By: Black Sun
- Diff: `main...39d805c`
- Axes: code, functional, relevancy
- Verdict: approve
- Score: 18/18 met, 0 unmet, 0 unverified at runtime, 0 out of the diff

### Criteria
- [x] P1.1 `uv sync --locked` and `check --deploy` pass — pre-commit this round: 8/8 Passed
- [x] P1.2 audit contract green on fake and PostgreSQL; failing audit rolls back the write — tests/contracts/test_unit_of_work.py:59; `uv run pytest` 271 passed, 3 deselected
- [x] P1.3 cross-origin POST → 403; same-origin and no-Origin pass — access.feature:47, tests/api/test_same_origin.py
- [x] P1.4 unknown page renders the 404 in the layout — tests/api/test_same_origin.py
- [x] P2.1 domain reached through use-case scenarios only — tests/use_cases/identity/
- [x] P2.2 sign_in and lockout features green; contracts on PostgreSQL and Redis — sign_in.feature, lockout.feature, tests/contracts/test_failed_sign_ins.py; 271 passed
- [x] P2.3 access.feature green; redirect, 403 and role homes — access.feature:11,21
- [x] P2.4 change_password.feature green, forced change enforced — change_password.feature:27
- [x] P3.1 invalid values refused with field messages — hospitals.feature:10, appointment_types.feature:14, rooms.feature:14
- [x] P3.2 deletion refusals green; failing audit leaves no record — rooms.feature:45, appointment_types.feature:60, departments.feature:43, hospitals.feature:56; tests/integration/test_reference_queries_postgres.py:65
- [x] P3.3 25 rows → pages of 20 and 5, total 25, search narrows — tests/integration/test_reference_queries_postgres.py:23,34; rooms.feature:24 now 21 rows, page 2
- [x] P3.4 admin creates and edits each entity through the client; clinician 403 — tests/api/test_console_reference.py:94,165,205
- [x] P4.1 manage_users.feature green; deactivated session rejected in integration — tests/api/test_console_users.py:47
- [x] P4.2 clinician_profiles.feature and clinician refusals green — clinician_profiles.feature:41-56,71,77
- [x] P4.3 admin client attaches a profile; lint-imports green — tests/api/test_console_users.py:79; `Contracts: 6 kept, 0 broken.`
- [x] P5.1 seed reruns without duplicates — tests/integration/test_seed.py:21
- [x] P5.2 `pytest -m e2e` green against localhost:8000 — rerun: `3 passed, 271 deselected`
- [x] P5.3 docs name contexts and commands; pre-commit green — plan.md Decisions gained the profile decision; pre-commit 8/8 Passed

### Findings
- `src/drlibre/organisation/infrastructure/repositories.py:64` : when `protected_objects` is empty, `refuse_if_any` raises nothing and the `except` exits silently, so the use case audits "deleted" for a row still stored; the nested try only re-chains the cause → end the except block with an unconditional has_dependents raise from `error`, so an empty list cannot pass silently — 🟢 minor, error-handling
- `tests/features/identity/manage_users.feature:26` : « Règle §10 : ... de 10 à 72 caractères » — §10 names the temporary password; the 10-72 length is stated in §8 (password change), and only the lower bound is tested → cite §8 + §10, add a 73-character row — 🟢 minor, conform
- `tests/integration/test_reference_queries_postgres.py:65` : the name says "a child added after the check", the test calls the repository delete directly with no check before it → name it "the repository itself refuses a protected delete, listing the child" — 🟢 minor, fit
