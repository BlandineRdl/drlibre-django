---
status: pending
---

# Instruction: `Patient` et écritures conditionnelles `If-Match`

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/
│   ├── interop/
│   │   ├── application/ports/inbound.py                           ✏️  `PatientReads`, `ConditionalWrites`, `WriteTarget`
│   │   ├── infrastructure/sql_patients.py                         ✅  patient lui-même, patients du praticien (au moins un RDV), admin ; `name`, `email`, `phone`, `birthdate`
│   │   └── infrastructure/conditional_writes.py                   ✅  transaction externe, verrous dans l'ordre du produit, version recalculée, 412
│   └── interfaces/fhir/
│       ├── schemas/patient.py                                     ✅  `Patient`
│       ├── diff.py                                                ✅  changements autorisés, `invalid_input` / `forbidden` sinon
│       ├── routers/patients.py                                    ✅  `read`, `search-type`, `update` (patient : téléphone, date de naissance → `UpdateProfile`)
│       ├── outcome.py                                             ✏️  412 `conflict` « version périmée »
│       └── registry.py                                            ✏️  `Patient`
└── tests/
    ├── features/fhir/un_client_agit_avec_le_jeton_d_un_utilisateur_et_exactement_ses_droits.feature  ✏️  puces `Patient`, `If-Match`, audit
    ├── fhir/test_un_client_agit_avec_le_jeton_d_un_utilisateur_et_exactement_ses_droits.py  ✏️
    ├── contracts/test_interop_patients.py                         ✅  fake vs SQL
    └── integration/test_concurrent_conditional_writes_postgres.py ✅  deux `PUT` même version : un 200, un 412
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | deux patients, un praticien avec un RDV du premier, un admin | prêt | system |
| Happy path   | jeton patient `GET /fhir/Patient/<soi>` | nom, date de naissance, email, téléphone, actif | api |
| Happy path   | jeton praticien `GET /fhir/Patient?name=…` | seulement ses patients | api |
| Happy path   | jeton patient `PUT /fhir/Patient/<soi>` téléphone et date changés, `If-Match` courant | 200, nouvelle version, audit `user.profile_updated` identique à l'écran | api |
| Edge case    | jeton patient `GET /fhir/Patient/<autre>` | 403 `forbidden` | api |
| Edge case    | `GET /fhir/Patient/<absent>` | 404 | api |
| Edge case    | `PUT` avec `If-Match` périmé | 412, rien écrit | api |
| Edge case    | patient change son nom ou son email | 400 `invalid_input` sur le champ | api |
| Edge case    | deux `PUT` concurrents avec la même version | un 200, un 412 | system |
| Teardown     | base vidée | baseline | system |

## Tasks to do

### `1)` Lectures `Patient`

> Visibles selon §15.4.

1. SQL limité au lecteur, paramètres `name`, `email`, `phone`, `birthdate`, `_sort` `name` ; fake et contrat.

### `2)` `ConditionalWrites`

> `If-Match` comparé sous les verrous de l'écriture.

1. Cibles et ordre : RDV (profil, patient, ligne), utilisateur (ligne), `Schedule`/`PractitionerRole` (profil puis ligne), référentiel (ordre de son use case, phase 9).
2. L'unité de travail du use case s'emboîte en savepoint ; e-mails toujours envoyés au commit.
3. Test de course `transaction=True` par cible livrée, qui échoue sans le verrou ; exception consignée phase 11 dans architecture.md.

### `3)` `update` `Patient`

> Patient : téléphone et date de naissance seulement.

1. `diff` réutilisable par les phases suivantes ; `UpdateProfile` appelé ; admin traité en phase 9.

### `4)` Scénarios

> Puces `Patient`, recherches, `If-Match`, audit.

1. Noms identiques aux puces.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | autre fiche existante → 403, absente → 404 |
| 2 | course : un 200, un 412 ; sans verrou le test échoue |
| 3 | audit de la mise à jour FHIR = audit de l'écran profil |
| 4 | scénarios verts sur PostgreSQL |
