---
status: done
---

# Instruction: Créneaux `Slot`

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/
│   ├── scheduling/
│   │   ├── domain/slot.py                                         ✏️  `SlotState(clinician_id, rule_id, start, end, status)`
│   │   ├── application/ports/inbound.py                           ✏️  `FindSlotStates`
│   │   ├── application/use_cases/find_free_slots.py               ✏️  calcul partagé avec `FindSlotStates`
│   │   └── application/use_cases/find_slot_states.py              ✅  `free`, `busy`, `busy-tentative`, `busy-unavailable`
│   ├── bootstrap/container.py                                     ✏️  `find_slot_states`
│   └── interfaces/fhir/
│       ├── slot_id.py                                             ✅  base32 (profil, type, début) ↔ id
│       ├── schemas/slot.py                                        ✅  `Slot`
│       ├── routers/slots.py                                       ✅  `read`, `search-type`, `_include` `Slot:schedule`
│       └── registry.py                                            ✏️  `Slot`
└── tests/
    ├── features/scheduling/les_plages_du_praticien_donnent_ses_creneaux_libres.feature  ✏️  `Règle §15.2 : …` états des créneaux
    ├── use_cases/scheduling/                                      ✏️  steps `FindSlotStates` sur fakes
    ├── properties/test_slot_states.py                             ✅  Hypothesis : les `free` de `FindSlotStates` = `FindFreeSlots`
    ├── features/fhir/un_client_sans_jeton_decouvre_le_referentiel_et_les_creneaux_libres.feature  ✏️  puces `Slot`
    ├── features/fhir/un_client_agit_avec_le_jeton_d_un_utilisateur_et_exactement_ses_droits.feature  ✏️  statuts `busy*` pour le personnel
    └── fhir/test_slot_id.py                                       ✅  aller-retour, longueur ≤ 64, alphabet FHIR
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | praticien avec plages, un RDV, une retenue, une absence | prêt | system |
| Happy path   | `GET /fhir/Slot?service-type=<type>&start=ge…&start=lt…` sans jeton | créneaux libres de §5.1 seulement, `schedule` = la plage | api |
| Happy path   | même recherche deux fois | mêmes ids | api |
| Happy path   | `GET /fhir/Slot/<id>` | le créneau, `free` | api |
| Happy path   | jeton praticien `status=busy,busy-tentative,busy-unavailable` | RDV, retenue, absence marqués | api |
| Edge case    | sans `service-type`, ou plage `start` > 31 jours, ou sans borne | 400 `invalid_input` | api |
| Edge case    | `status=busy` sans jeton ou jeton patient | 403 `forbidden` | api |
| Edge case    | `schedule.actor=Practitioner/<id>`, ou `schedule=Schedule/<id>` | créneaux de ce praticien, ou de cette plage | api |
| Edge case    | `_include=Slot:schedule` | `Schedule` inclus | api |
| Edge case    | fenêtre coupée par le délai ou l'horizon (fin de semaine tardive) | aucun créneau, pas d'erreur | api |
| Teardown     | base vidée | baseline | system |

## Tasks to do

### `1)` `FindSlotStates`

> Un seul calcul des créneaux libres, états marqués à côté.

1. Extraire de `FindFreeSlots` la requête des libres en gardant `clinician_id` ; `FindSlotStates` (praticien facultatif) y ajoute plage et état, une lecture pour tout le département.
2. Fake, steps et propriété Hypothesis d'équivalence.

### `2)` Ressource `Slot`

> Ids stables et décodables.

1. `slot_id` encode et décode ; id mal formé → 404.
2. Routes, `schedule.actor` traduit en profil, `status` réservé au personnel, plage ≤ 31 jours.

### `3)` Scénarios

> Puces `Slot` des deux Stories.

1. Puce « Une recherche `Slot` exige… » et puce statuts du personnel.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | propriété : ensembles `free` égaux ; `tests/features/scheduling` vert |
| 2 | `tests/fhir/test_slot_id.py` vert ; lecture d'un id stable |
| 3 | scénarios `Slot` verts sur PostgreSQL |
