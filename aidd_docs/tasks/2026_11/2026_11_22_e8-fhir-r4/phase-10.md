---
status: pending
---

# Instruction: Disponibilités du praticien

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/fhir/
│   ├── mappers/schedule.py                                        ✅  `Schedule` ↔ `fields` de `SaveAvailabilityRule` (extension jour, heures, pas ; salle acteur)
│   ├── routers/directory.py                                       ✏️  `Schedule` `create`, `update`, `delete` ; `PractitionerRole` `update` du praticien : diff `notAvailable`
│   └── registry.py                                                ✏️
└── tests/
    ├── features/fhir/le_praticien_gere_ses_disponibilites_en_fhir.feature  ✅
    └── fhir/test_le_praticien_gere_ses_disponibilites_en_fhir.py  ✅
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | deux praticiens avec profil, une salle de chaque département, un RDV réservé | prêt | system |
| Happy path   | praticien `POST /fhir/Schedule` | 201 ; reflétée dans `PractitionerRole.availableTime` ; nouveaux `Slot` | api |
| Happy path   | praticien `PUT` puis `DELETE` sa `Schedule` | 200 / 204 ; `Slot` à jour ; audits `availability_rule.*` | api |
| Happy path   | praticien `PUT /fhir/PractitionerRole/<soi>` ajoute une période `notAvailable` | absence créée ; `Slot` de la période retirés ; RDV réservé conservé | api |
| Happy path   | même `PUT` qui retire la période | absence supprimée | api |
| Edge case    | `Schedule` d'un autre praticien ; admin écrit une `Schedule` | 403 | api |
| Edge case    | salle d'un autre département, chevauchement, pas hors 5–240, fin avant début | 400 `invalid_input` | api |
| Edge case    | `planningHorizon` changé | 400 `invalid_input` | api |
| Edge case    | praticien change autre chose que `notAvailable` | 403 | api |
| Edge case    | période identique déjà enregistrée | 400 `invalid_input` | api |
| Edge case    | `If-Match` périmé | 412 | api |
| Teardown     | base vidée | baseline | system |

## Tasks to do

### `1)` `Schedule`

> Mêmes use cases que l'écran des plages.

1. Mapper, `create`/`update`/`delete`, `If-Match`.

### `2)` Absences par `PractitionerRole`

> Diff de `notAvailable`, tout ou rien.

1. Ajouts → `RecordTimeOff`, retraits → `DeleteTimeOff`, dans `ConditionalWrites`.

### `3)` Scénarios

> Toutes les puces de la Story.

1. Noms identiques aux puces.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | `Slot` reflètent aussitôt chaque changement |
| 2 | échec d'une période → aucune écrite |
| 3 | scénarios verts sur PostgreSQL |
