---
status: pending
---

# Instruction: Socle FHIR et jetons bearer

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── config/
│   ├── middleware.py                                              ✏️  `/fhir/` exempté (bearer seul, pas de cookie)
│   └── urls.py                                                    ✏️  `path("fhir/", fhir.urls)`
├── pyproject.toml                                                 ✏️  contrats import-linter : `drlibre.interop` lecture seule, `interfaces.fhir` sous la règle interfaces
├── src/drlibre/
│   ├── bootstrap/container.py                                     ✏️  jetons, `interop`
│   ├── identity/
│   │   ├── application/ports/inbound.py                           ✏️  `IssueApiToken`, `RevokeApiTokens`, `AuthenticateToken`
│   │   ├── application/ports/outbound.py                          ✏️  `ApiTokens`
│   │   ├── application/use_cases/api_tokens.py                    ✅  émettre, révoquer, authentifier
│   │   ├── domain/api_token.py                                    ✅  `ApiToken` (hash, utilisateur, libellé, expiration)
│   │   └── infrastructure/
│   │       ├── django/models.py                                   ✏️  `ApiTokenRecord`
│   │       ├── django/migrations/0005_api_token.py                ✅
│   │       ├── django/management/__init__.py                      ✅
│   │       ├── django/management/commands/__init__.py             ✅
│   │       ├── django/management/commands/api_token.py            ✅  `api_token <email> [--days N] [--revoke]`
│   │       └── repositories.py                                    ✏️  `DjangoApiTokens`
│   ├── interop/                                                   ✅  contexte lecture seule (domain, application, infrastructure)
│   │   ├── application/ports/inbound.py                           ✅  `Readers`, `Reader`
│   │   └── infrastructure/sql_readers.py                          ✅  profil → praticien, admin, patient
│   └── interfaces/
│       ├── web/auth.py                                            ✏️  `Authorization: Bearer` ; cookie ignoré sous `/fhir`
│       ├── web/views/errors.py                                    ✏️  `/fhir/` hors pages d'erreur
│       └── fhir/
│           ├── __init__.py                                        ✅  `NinjaAPI` `/fhir`, rendu et parse `application/fhir+json`, handlers
│           ├── outcome.py                                         ✅  `DomainError` → `OperationOutcome`
│           ├── bundle.py                                          ✅  `searchset`, `total`, `self`/`next`/`previous`, `_count`, `_page`, `_sort`
│           ├── version.py                                         ✅  `versionId`, `lastUpdated`, `ETag`
│           ├── registry.py                                        ✅  interactions, paramètres, `_include`, `_sort` par ressource
│           ├── params.py                                          ✅  refus des paramètres non déclarés, préfixes `date`, références
│           ├── schemas/                                           ✅  Pydantic R4 : `Meta`, `Reference`, `Coding`, `Extension`, `OperationOutcome`, `Bundle`
│           └── metadata.py                                        ✅  `GET /fhir/metadata` depuis le registre (ressources ajoutées phase par phase)
├── scripts/seed.py                                                ✏️  un jeton de démo par rôle
└── tests/
    ├── features/identity/un_client_agit_avec_le_jeton_d_un_utilisateur_et_exactement_ses_droits.feature  ✅  puces jeton
    ├── use_cases/identity/test_api_tokens.py                      ✅  steps sur fakes
    ├── fakes/api_tokens.py                                        ✅  `InMemoryApiTokens`
    ├── fakes/world.py                                             ✏️  jetons câblés
    ├── contracts/test_api_tokens.py                               ✅  fake vs Django
    └── fhir/
        ├── conftest.py                                            ✅  client FHIR, jeton par rôle, scène
        ├── test_conventions.py                                    ✅  type de contenu, `OperationOutcome`, 401, 405, `_count`
        └── test_metadata.py                                       ✅  `CapabilityStatement` 4.0.1
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | utilisateurs admin, praticien, patient ; jeton émis pour chacun | prêt | system |
| Happy path   | `manage.py api_token patient@… ` | jeton affiché une fois, seul son hash stocké, audit `identity.api_token_issued` | cli |
| Happy path   | `GET /fhir/metadata` sans jeton | 200 `application/fhir+json`, `fhirVersion` `4.0.1` | api |
| Edge case    | `Authorization: Bearer faux` | 401 `OperationOutcome` `login` | api |
| Edge case    | jeton d'un utilisateur désactivé ou expiré | 401 | api |
| Edge case    | `--revoke` puis appel | 401 | cli, api |
| Edge case    | jeton d'un utilisateur `must_change_password` | 403 `forbidden` | api |
| Edge case    | `DELETE /fhir/metadata` | 405 `not-supported` | api |
| Edge case    | cookie de session valide seul sur `/fhir` | traité comme anonyme | api |
| Teardown     | base vidée | baseline | system |

## Tasks to do

### `1)` Jetons d'API

> Un jeton porte exactement les droits d'un utilisateur actif.

1. `ApiToken` + `ApiTokenRecord` + migration ; `hash_token`, `SecretsTokenGenerator` réutilisés.
2. `IssueApiToken`, `RevokeApiTokens`, `AuthenticateToken` (inconnu, expiré, inactif → `None`), audités.
3. Commande `api_token` ; fake et contrat.

### `2)` Authentification bearer

> `request.drlibre_identity` vient du jeton.

1. `SessionMiddleware` : `Authorization: Bearer` → `AuthenticateToken`, `act_as` ; sous `/fhir` le cookie est ignoré.
2. `SameOriginMiddleware`, `DomainErrorPagesMiddleware` : `/fhir/` exempté ; `Identity` du jeton : expiration du jeton, `session_renewed=False` ; `must_change_password` → 403.

### `3)` Porte `/fhir`

> Conventions §15.1 communes à toutes les ressources.

1. `NinjaAPI` séparé, rendu `application/fhir+json`, parse `application/fhir+json` et `application/json`.
2. `OperationOutcome` pour `DomainError` et la validation (mapping du plan).
3. Bundle `searchset` paginé (`_count` défaut 20, ramené à 100), liens absolus depuis `PUBLIC_BASE_URL`.
4. `versionId` en empreinte, `ETag`, `meta.lastUpdated`.
5. Registre + refus des paramètres non déclarés + 405 sur interaction non déclarée, avant l'authentification ; écriture déclarée sans jeton → 401.
6. `GET /fhir/metadata` construit depuis le registre.

### `4)` Contexte `interop`

> Socle de lecture limité au lecteur.

1. Paquet `drlibre.interop` (domain, application, infrastructure) ; `Readers.of(user_id) -> Reader`.
2. Contrats import-linter : cœur sans autre contexte ; couches.

### `5)` Seed

> Un jeton de démo par rôle, idempotent.

1. Jetons fixes `demo-admin-token`, `demo-clinician-token`, `demo-patient-token` hachés ; relancer ne duplique rien.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | scénarios « Une commande d'administration émet un jeton… » et « Un jeton invalide renvoie `unauthenticated` (401)… » verts sur fakes ; contrat fake = Django |
| 2 | `tests/api/test_same_origin.py`, `tests/api/test_domain_errors.py` verts ; bearer accepté, cookie ignoré sous `/fhir` |
| 3 | `tests/fhir/test_conventions.py` : type de contenu, 401, 405, `_count=500` → 100 au plus, paramètre inconnu → 400 `OperationOutcome` |
| 4 | `uv run lint-imports` vert |
| 5 | `python -m scripts.seed` deux fois : trois jetons, les trois authentifient |
