---
status: done
---

# Instruction: Référentiel public en lecture

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/
│   ├── interop/
│   │   ├── domain/rows.py                                         ✅  lignes versionnées : hôpital, département, salle, type, spécialité, praticien, profil, plage, absence
│   │   ├── application/ports/inbound.py                           ✏️  `DirectoryReads` : `read`, `search` par ressource, avec `Reader`
│   │   └── infrastructure/sql_directory.py                        ✅  SQL : actifs seulement pour l'anonyme, champs du personnel, `near`, `_sort`, total
│   └── interfaces/fhir/
│       ├── schemas/directory.py                                   ✅  `Organization`, `Location`, `HealthcareService`, `CodeSystem`, `ValueSet`, `Practitioner`, `PractitionerRole`, `Schedule`
│       ├── mappers/directory.py                                   ✅  ligne → ressource, extensions
│       ├── routers/directory.py                                   ✅  `read` et `search-type`, `_include` `PractitionerRole:practitioner|organization`
│       └── registry.py                                            ✏️  ces ressources
└── tests/
    ├── features/fhir/un_client_sans_jeton_decouvre_le_referentiel_et_les_creneaux_libres.feature  ✅  puces hors `Slot`
    ├── features/fhir/un_client_agit_avec_le_jeton_d_un_utilisateur_et_exactement_ses_droits.feature  ✅  puce champs du personnel (`Practitioner`, `PractitionerRole`, admins)
    ├── fhir/test_un_client_sans_jeton_decouvre_le_referentiel_et_les_creneaux_libres.py  ✅  steps PostgreSQL
    ├── fhir/test_un_client_agit_avec_le_jeton_d_un_utilisateur_et_exactement_ses_droits.py  ✅  steps PostgreSQL
    └── contracts/test_interop_directory.py                        ✅  fake vs SQL
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | deux hôpitaux, un inactif ; départements, salles, types, spécialités, praticiens actif et inactif, plages | prêt | system |
| Happy path   | `GET /fhir/Organization?type=prov&address-city=…` | Bundle `searchset`, `total`, liens, ressources avec `meta.versionId` | api |
| Happy path   | `GET /fhir/Location/<hôpital>` | site avec adresse, téléphone, `position`, fuseau ; salle `partOf` le site | api |
| Happy path   | `GET /fhir/PractitionerRole?specialty=…&_include=PractitionerRole:practitioner` | rôles + `Practitioner` inclus en `mode: include` | api |
| Happy path   | `GET /fhir/CodeSystem?status=active`, `ValueSet/specialties` | une `CodeSystem` par spécialité active ; `ValueSet` qui les réunit | api |
| Happy path   | `GET /fhir/Schedule?actor=Practitioner/<id>&date=…&active=true` | plages du praticien valides à cette date | api |
| Edge case    | hôpital inactif ou id absent, sans jeton | 404 `not-found` | api |
| Edge case    | `Practitioner` sans jeton | ni email ni téléphone | api |
| Edge case    | même lecture avec jeton praticien ou admin | email, téléphone, poids round robin | api |
| Edge case    | `Practitioner` d'un admin, jeton praticien puis admin | 404 puis 200 avec `PractitionerRole` codé admin | api |
| Edge case    | `_count=2&_sort=-name` | 2 entrées triées, lien `next` | api |
| Edge case    | `Location?near=lat|lon|10|km` | sites à moins de 10 km | api |
| Teardown     | base vidée | baseline | system |

## Tasks to do

### `1)` Lectures `interop` du référentiel

> Une lecture SQL par ressource, limitée au lecteur, versionnée.

1. Lignes gelées avec `updated_at` (et pour le profil : plages et absences).
2. `read(id, reader)` et `search(params, reader, page) -> Page` ; anonyme : actifs, champs publics.
3. Paramètres du §15.5 pour ces ressources, `near`, `_sort` déclarés ; fake et contrat.

### `2)` Ressources et routes

> Correspondance §15.2.

1. Schémas et mappers ; extensions sous `<PUBLIC_BASE_URL>/fhir/StructureDefinition/<nom>`.
2. Routes `read` + `search-type`, `_include` du praticien et de l'organisation.
3. Registre mis à jour.

### `3)` Scénarios

> Puces de la Story « sans jeton » (hors `Slot`) et la puce champs du personnel.

1. Un scénario par puce, noms identiques aux puces.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | contrat fake = SQL ; inactif → absent pour l'anonyme |
| 2 | chaque ressource porte l'id produit, `meta.versionId`, `meta.lastUpdated` |
| 3 | `uv run pytest tests/fhir tests/test_acceptance_names.py` vert |
