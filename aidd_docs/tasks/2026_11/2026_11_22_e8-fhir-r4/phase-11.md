---
status: pending
---

# Instruction: CapabilityStatement, preuve de l'Epic, seed, documentation, gates

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── README.md                                                      ✏️  jetons de démo, exemples `curl` FHIR
├── aidd_docs/
│   ├── backlog/open-questions.md                                  ✏️  réponses E8
│   ├── memory/architecture.md                                     ✏️  façade FHIR, interop, jetons, `If-Match`, ids `Slot`, id d'entrée acceptée
│   ├── memory/codebase-map.md                                     ✏️  `interop`, `interfaces/fhir`, `tests/fhir`
│   ├── memory/coding-assertions.md                                ✏️  `curl -i localhost:8000/fhir/metadata`
│   ├── memory/testing.md                                          ✏️  contrat FHIR
│   └── tasks/2026_11/2026_11_22_e8-fhir-r4/load-results.md        ✅  p95 de la recherche `Slot` FHIR
├── loadtests/locustfile.py                                        ✏️  tâche « recherche `Slot` FHIR »
├── src/drlibre/interfaces/fhir/metadata.py                        ✏️  complet : ressources, interactions, paramètres, `_include`, `_sort`
└── tests/
    ├── features/fhir/un_client_decouvre_les_capacites_du_serveur_dans_le_capabilitystatement.feature  ✅
    ├── fhir/test_un_client_decouvre_les_capacites_du_serveur_dans_le_capabilitystatement.py  ✅  registre ↔ routes dans les deux sens
    └── fhir/test_parcours_fhir_de_l_epic.py                       ✅  `Slot` libre sans jeton → réservation patient de démo `booked` → annulation ; audit et notification = écran ; patient ne voit ni RDV ni `Patient` d'un autre
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | `docker compose up -d --build` (seed démo, jetons) | prêt | system |
| Happy path   | `GET /fhir/metadata` sans jeton | `CapabilityStatement` 4.0.1 `application/fhir+json` | api |
| Happy path   | chaque route Ninja `/fhir` | déclarée ; chaque interaction déclarée a sa route | system |
| Happy path   | parcours de l'Epic avec le jeton patient de démo | `booked` avec praticien et salle, puis `cancelled` ; audit et notification identiques à l'écran | api |
| Edge case    | jeton patient sur RDV et `Patient` d'un autre | 403 ; recherches sans eux | api |
| Edge case    | chaque écriture déclarée, sans jeton | 401 | api |
| Happy path   | `./scripts/load-run.sh` | p95 recherche `Slot` FHIR < 200 ms consigné | cli |
| Happy path   | gates | tous verts | cli |
| Teardown     | projet de charge supprimé | baseline | cli |

## Tasks to do

### `1)` CapabilityStatement complet

> Déclaré = servi.

1. `metadata` depuis le registre final ; test dans les deux sens (routes Ninja ↔ registre, paramètres refusés hors registre).
2. Scénarios de la Story.

### `2)` Preuve de l'Epic

> Section *Success Evidence*.

1. Parcours sur la seed de démo ; scénario « même refus que l'écran » vérifié présent pour chaque écriture FHIR (liste des phases 4–10).

### `3)` Charge

> p95 de la recherche `Slot` FHIR.

1. Tâche Locust, `./scripts/load-run.sh`, `load-results.md`.

### `4)` Documentation

> Mémoire et questions ouvertes à jour.

1. Fichiers listés ci-dessus ; réponses E8 reprises des Decisions du plan.

### `5)` Gates

> Contributor checks.

1. `uv run ruff check .`, `uv run ruff format --check .`, `uv run lint-imports`, `uv run pre-commit run --all-files`, `uv run pytest`, `uv run pytest -m e2e` (non-régression), `curl -i localhost:8000/fhir/metadata`.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | test registre ↔ routes vert |
| 2 | parcours vert sur la stack compose |
| 3 | p95 consigné ; < 200 ms ou écart expliqué |
| 4 | mémoire décrit `interop`, `/fhir`, jetons |
| 5 | toutes les gates vertes |
