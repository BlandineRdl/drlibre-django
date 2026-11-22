# Run: E8 - Un client FHIR R4 fait tout ce que les écrans permettent, ni plus ni moins
## Run 1
- Head: `ad7dc3a`
- Left: none; `ValueSet` read-only deviation recorded in `open-questions.md`, to raise in the PR

| Task | Validation | Result |
| --- | --- | --- |
| 1.1 | Jetons d'API: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 1 of `assert.md`) |
| 1.2 | Authentification bearer: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 1 of `assert.md`) |
| 1.3 | Porte `/fhir`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 1 of `assert.md`) |
| 1.4 | Contexte `interop`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 1 of `assert.md`) |
| 1.5 | Seed: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 1 of `assert.md`) |
| 2.1 | Lectures `interop` du référentiel: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 2 of `assert.md`) |
| 2.2 | Ressources et routes: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 2 of `assert.md`) |
| 2.3 | Scénarios: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 2 of `assert.md`) |
| 3.1 | `FindSlotStates`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 3 of `assert.md`) |
| 3.2 | Ressource `Slot`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 3 of `assert.md`) |
| 3.3 | Scénarios: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 3 of `assert.md`) |
| 4.1 | Lectures `Patient`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 4 of `assert.md`) |
| 4.2 | `ConditionalWrites`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 4 of `assert.md`) |
| 4.3 | `update` `Patient`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 4 of `assert.md`) |
| 4.4 | Scénarios: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 4 of `assert.md`) |
| 5.1 | Lectures `Appointment`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 5 of `assert.md`) |
| 5.2 | Ressource et réservation: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 5 of `assert.md`) |
| 5.3 | Scénarios: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 5 of `assert.md`) |
| 6.1 | `update` `Appointment`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 6 of `assert.md`) |
| 6.2 | Scénarios: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 6 of `assert.md`) |
| 7.1 | Une seule ressource: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 7 of `assert.md`) |
| 7.2 | Inscription et acceptation FHIR: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 7 of `assert.md`) |
| 7.3 | Scénarios: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 7 of `assert.md`) |
| 8.1 | `Communication`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 8 of `assert.md`) |
| 8.2 | `AuditEvent`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 8 of `assert.md`) |
| 8.3 | Scénarios: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 8 of `assert.md`) |
| 9.1 | Garde et mappers d'écriture: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 9 of `assert.md`) |
| 9.2 | Routes d'écriture: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 9 of `assert.md`) |
| 9.3 | Scénarios: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 9 of `assert.md`) |
| 10.1 | `Schedule`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 10 of `assert.md`) |
| 10.2 | Absences par `PractitionerRole`: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 10 of `assert.md`) |
| 10.3 | Scénarios: its phase's scenarios and contract tests in the full `uv run pytest` | green within 2108 passed (round 10 of `assert.md`) |
| 11.1 | CapabilityStatement Story scenarios, `uv run pytest tests/fhir` | 345 passed |
| 11.2 | Epic journey and refusal map, `uv run pytest tests/fhir/test_parcours_fhir_de_l_epic.py` | 3 passed |
| 11.3 | `./scripts/load-run.sh` | FHIR `Slot` p95 88 ms, 0 failures |
| 11.4 | memory, README, open questions | `interop`, `/fhir`, tokens described |
| 11.5 | `uv run pre-commit run --all-files`, `uv run pytest`, `uv run pytest -m e2e`, `curl -i localhost:8000/fhir/metadata` | all exit 0; 2108 passed; 11 e2e passed; 200 `application/fhir+json` |
