---
status: pending
---

# Instruction: Lectures admin : RDV, export, patients, audit, rappels
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/booking/
│   ├── application/ports/inbound.py                            ✏️  `AdminAppointmentFilter`, `ListAllAppointments`, `ExportAppointments`, `RunReminders`
│   ├── application/ports/outbound.py                           ✏️  `AdminAppointments` (page, all)
│   ├── application/use_cases/list_all_appointments.py          ✅  admin seul, page de 20
│   ├── application/use_cases/export_appointments.py            ✅  admin seul, audit `{count}`
│   ├── application/use_cases/run_reminders.py                  ✅  admin seul, appelle `SendReminders`
│   ├── infrastructure/admin_appointments.py                    ✅  `SqlAdminAppointments`
│   └── infrastructure/django/{models.py,migrations/0005_appointment_start_index.py} ✏️✅  index `start`
├── src/drlibre/audit/
│   ├── application/ports/inbound.py                            ✏️  `AuditFilter`, `AuditRow`, `page`, `entity_types`
│   └── infrastructure/queries.py                               ✏️  page filtrée, plus récent d'abord
├── src/drlibre/identity/
│   ├── application/ports/inbound.py                            ✏️  `PatientLookup.active_patients`
│   └── infrastructure/queries.py                               ✏️  patients actifs par nom ou email
├── src/drlibre/bootstrap/container.py                          ✏️  câblage
└── tests/
    ├── fakes/{booking.py,audit_actors.py,user_queries.py}       ✏️  fakes triviaux
    ├── contracts/{test_admin_appointments.py,test_audit_actors.py,test_identity_repositories.py} ✅✏️✏️  contrats `AdminAppointments`, `AuditQueries.page`, `PatientLookup`
    ├── features/booking/{l_admin_liste_les_rdv_de_tous_les_hopitaux,l_admin_exporte_les_rdv_filtres_en_csv,l_admin_consulte_la_politique_de_reservation_et_lance_les_rappels}.feature ✅
    ├── features/booking/l_admin_consulte_le_journal_d_audit.feature ✅  steps admin booking, lecture audit
    └── integration/test_admin_reads_postgres.py                 ✅  filtres, tri et fuseau en SQL (pytest-bdd sur PostgreSQL)
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | deux hôpitaux en fuseaux différents, RDV de tous statuts et sources, entrées d'audit | prêt | system |
| Happy path | liste filtrée par période, département, praticien, statut, source | RDV correspondants, plus récents d'abord, 20 par page, total, fuseau par ligne | system |
| Edge case | filtre ou page inutilisable | défaut appliqué | system |
| Happy path | export de l'ensemble filtré (25 lignes) | 25 lignes d'ids, instants UTC, audit `{count: 25}` | system |
| Happy path | journal filtré par acteur, type d'entité, période | entrées plus récentes d'abord, 20 par page, heure, acteur, action, entité, correlation id | system |
| Edge case | entrée d'échec de connexion, entrée de réservation provisoire avant vérification de l'email | acteur vide | system |
| Edge case | `UPDATE` ou `DELETE` sur une entrée d'audit | refusé par les triggers `audit.0002` (`tests/integration/test_audit_append_only_postgres.py`, rejoué) | system |
| Happy path | admin lance les rappels deux fois | rappels créés une seule fois, une entrée d'audit `{count}` au premier | system |
| Edge case | praticien ou patient lance la liste, l'export ou les rappels | `forbidden` | system |
| Teardown | base vidée | baseline | system |

## Tasks to do
### `1)` Liste et export
> Tous les hôpitaux, filtres combinables.

1. `AdminAppointmentFilter(start_date, end_date, department_id, clinician_id, status, source)` ; SQL jour local `(a.start AT TIME ZONE h.time_zone)::date`, tri `start DESC, id`.
2. `SqlAdminAppointments.page` (noms, fuseau) et `all` (ids seulement) ; index `appointment_start`.
3. `ListAllAppointments`, `ExportAppointments` : `Staff.is_admin` sinon `forbidden` ; export audité `booking.appointments_exported` `{count}`.

### `2)` Patients actifs
> Choisir le patient par nom ou email.

1. `PatientLookup.active_patients(text)` : rôle `PATIENT`, actif, `ILIKE`, 20 max.

### `3)` Journal d'audit
> Lecture seule filtrée.

1. `AuditQueries.page(filter, request)` et `entity_types()` ; `AuditRow(at, actor_id, action, entity_type, entity_id, correlation_id)`.

### `4)` Rappels à la demande
> Même job que le beat.

1. `RunReminders.execute(actor_id) -> int` admin seul.

### `5)` Acceptance
> Stories liste, export (colonnes et audit), journal, politique (bouton et unicité).

1. Quatre `.feature` sur fakes ; filtres et fuseau rejoués sur PostgreSQL ; contrats.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | filtres combinés exacts sur PostgreSQL, jour local par hôpital, ordre décroissant |
| 2 | un patient inactif ou un praticien n'apparaît jamais |
| 3 | entrées filtrées, total juste, correlation id présent |
| 4 | deux lancements, aucun doublon |
| 5 | `uv run pytest tests/use_cases tests/contracts tests/integration` vert |
