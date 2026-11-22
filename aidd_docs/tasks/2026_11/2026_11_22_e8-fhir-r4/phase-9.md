---
status: done
---

# Instruction: Gestion du référentiel par l'admin

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/fhir/
│   ├── access.py                                                  ✅  `require_admin(identity)`, miroir de `require_role(Role.ADMIN)` du web
│   ├── mappers/directory_writes.py                                ✅  ressource → `fields` des use cases (`SaveRecord`, profils, `SaveUser`)
│   ├── routers/directory.py                                       ✏️  `create`, `update`, `delete` : `Organization` (prov → hôpital, dept → département), `Location` (salles), `HealthcareService`, `CodeSystem/specialties`, `Practitioner`, `PractitionerRole`
│   ├── routers/patients.py                                        ✏️  admin `create`, `update`, `delete`
│   └── registry.py                                                ✏️  interactions d'écriture
└── tests/
    ├── features/fhir/l_admin_gere_le_referentiel_en_fhir.feature  ✅
    └── fhir/test_l_admin_gere_le_referentiel_en_fhir.py           ✅
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | admin, praticien, hôpital, département, salle, type, spécialité | prêt | system |
| Happy path   | admin `POST /fhir/Organization` `prov` | 201 ; `Organization` et `Location` site du même id ; audit `hospital.created` | api |
| Happy path   | admin `POST /fhir/Location` salle avec étage, capacité, équipements | 201 ; audit `room.created` | api |
| Happy path   | admin `POST /fhir/HealthcareService` avec durée, battement, couleur, salle exigée, réservable en ligne | 201 | api |
| Happy path   | admin `POST`, `PUT`, `DELETE /fhir/CodeSystem` | spécialité créée, modifiée, supprimée ; `ValueSet/specialties` suit | api |
| Happy path   | admin `POST /fhir/Practitioner` + `temporary-password`, puis `POST /fhir/PractitionerRole` avec poids | utilisateur praticien et profil ; mot de passe jamais renvoyé | api |
| Happy path   | admin crée, modifie, supprime un `Patient` | audits `user.created|updated|deleted` | api |
| Edge case    | jeton praticien ou patient écrit | 403 | api |
| Edge case    | code déjà utilisé | 400 `invalid_input` `code` | api |
| Edge case    | suppression avec dépendants | 409 `has_dependents` avec la liste | api |
| Edge case    | salle changée de département utilisée par défaut | 409 `has_dependents` | api |
| Edge case    | admin désactive son compte ou change son rôle | refus de la console | api |
| Edge case    | `If-Match` périmé ; deux `PUT` concurrents | 412 ; un 200 et un 412 | api |
| Edge case    | `POST /fhir/Location` site | 405 ou `invalid_input` (le site s'écrit par `Organization`) | api |
| Teardown     | base vidée | baseline | system |

## Tasks to do

### `1)` Garde et mappers d'écriture

> L'admin seul, mêmes use cases que la console.

1. `require_admin` à l'entrée de chaque écriture du référentiel.
2. Mappers vers les `fields` des use cases ; extensions de salle, type, profil ; `temporary-password` write-only.

### `2)` Routes d'écriture

> `create`, `update` (diff, `If-Match`), `delete`.

1. Toutes les ressources de la Story ; `CodeSystem` = une spécialité ; `ValueSet` en lecture (écart signalé).
2. Lire l'ordre des verrous de chaque use case du référentiel et l'appliquer dans `ConditionalWrites` ; test de course.
3. Registre.

### `3)` Scénarios

> Toutes les puces ; règles et audit comparés à la console.

1. Noms identiques aux puces.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | non-admin → 403 sur chaque écriture |
| 2 | même entrée d'audit que la console pour chaque écriture |
| 3 | scénarios verts sur PostgreSQL |
