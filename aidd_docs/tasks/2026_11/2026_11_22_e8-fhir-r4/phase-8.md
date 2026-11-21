---
status: pending
---

# Instruction: `Communication` et `AuditEvent`

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/
│   ├── interop/
│   │   ├── application/ports/inbound.py                           ✏️  `CommunicationReads`, `AuditEventReads`
│   │   ├── infrastructure/sql_communications.py                   ✅  destinataire seul ; `recipient`, `category`, `sent`
│   │   └── infrastructure/sql_audit_events.py                     ✅  admin seul ; `agent`, `entity`, `entity-type`, `action`, `date`
│   └── interfaces/fhir/
│       ├── schemas/communication.py                               ✅
│       ├── schemas/audit_event.py                                 ✅
│       ├── routers/communications.py                              ✅  `read`, `search-type`, `update` (`received` → `MarkNotificationRead`)
│       ├── routers/audit_events.py                                ✅  `read`, `search-type`
│       └── registry.py                                            ✏️  les deux ressources
└── tests/
    ├── features/fhir/un_client_lit_les_notifications_de_son_utilisateur_en_fhir.feature  ✅
    ├── features/fhir/l_admin_consulte_le_journal_d_audit_en_fhir.feature  ✅
    ├── fhir/test_un_client_lit_les_notifications_de_son_utilisateur_en_fhir.py  ✅
    ├── fhir/test_l_admin_consulte_le_journal_d_audit_en_fhir.py   ✅
    └── contracts/test_interop_communications_audit.py             ✅
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | notifications de deux patients, entrées d'audit dont une connexion | prêt | system |
| Happy path   | patient `GET /fhir/Communication?category=…` | ses notifications : destinataire, catégorie, texte, `sent`, `about` | api |
| Happy path   | patient `PUT` avec `received` | 200, lue | api |
| Happy path   | admin `GET /fhir/AuditEvent?action=E&date=ge…` | entrées avec action, heure, agent, entité, détails, correlation id ; connexion `auth.login_succeeded` présente | api |
| Edge case    | patient lit la `Communication` d'un autre | 403 | api |
| Edge case    | `POST`/`DELETE` `Communication` | 405 | api |
| Edge case    | `PUT` qui change le texte | 400 `invalid_input` | api |
| Edge case    | praticien ou patient `GET /fhir/AuditEvent` | 403 | api |
| Edge case    | `POST`/`PUT`/`DELETE` `AuditEvent` | 405 | api |
| Teardown     | base vidée | baseline | system |

## Tasks to do

### `1)` `Communication`

> Le destinataire lit et marque comme lu.

1. SQL, mapper, routes ; `received` seul modifiable.

### `2)` `AuditEvent`

> L'admin lit le journal.

1. SQL sur `audit_auditentryrecord` (index `(entity_type, entity_id, at)`), mapper C/U/D/E, références FHIR des entités servies.
2. Garde admin par `Reader`.

### `3)` Scénarios

> Toutes les puces des deux Stories.

1. Noms identiques aux puces.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | lecture marquée par FHIR = lue au portail |
| 2 | aucune donnée personnelle hors des métadonnées déjà auditées |
| 3 | scénarios verts sur PostgreSQL |
