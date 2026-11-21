---
status: done
---

# Instruction: Contexte reporting : indicateurs, jours, praticiens chargés
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/reporting/                                      ✅
│   ├── domain/dashboard.py                                     ✅  `Range`, `Ratio`, `Dashboard`, `DayCount`, `BusyClinician`
│   ├── domain/available_minutes.py                             ✅  plages moins absences, par jour local
│   ├── application/ports/inbound.py                            ✅  `ViewDashboard`
│   ├── application/ports/outbound.py                           ✅  `ActivityQueries` (comptes, plages, absences)
│   ├── application/use_cases/view_dashboard.py                 ✅  admin seul, assemble les indicateurs
│   └── infrastructure/sql_activity.py                          ✅  `SqlActivityQueries`
├── pyproject.toml                                              ✏️  `drlibre.reporting` dans `layers`, contrat forbidden
├── src/drlibre/bootstrap/container.py                          ✏️  câblage
└── tests/
    ├── fakes/reporting.py                                       ✅
    ├── contracts/test_reporting_queries.py                      ✅
    ├── use_cases/reporting/test_available_minutes_properties.py ✅  Hypothesis
    ├── features/reporting/{l_admin_suit_les_indicateurs_du_tableau_de_bord,l_admin_voit_les_rdv_par_jour_et_les_praticiens_les_plus_charges}.feature ✅
    └── integration/test_dashboard_postgres.py                   ✅  chaque indicateur recalculé sur la seed de test
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | deux hôpitaux (Paris, Cayenne), plages, absences, RDV dans tous les statuts et sources, entrées `WAITING`/`OFFERED`/`BOOKED` | prêt | system |
| Happy path | période 7 jours | RDV, annulations, utilisation, absences, part en ligne, liste d'attente égaux à leur définition §13 | system |
| Edge case | `?range=` inutilisable | 7 jours | system |
| Edge case | aucun RDV, aucune plage | « n/a » pour chaque ratio, jamais 0 % | system |
| Edge case | RDV à 23:30 Cayenne (lendemain UTC) | compté dans le jour local de Cayenne | system |
| Happy path | histogramme et top 5 sur 30 jours | un compte par jour, 5 praticiens classés, égalité par nom | system |
| Edge case | patient ou praticien | `forbidden` | system |
| Teardown | base vidée | baseline | system |

## Tasks to do
### `1)` Domaine
> Définitions §13 en Python pur.

1. `Range.parse(raw)` : `today`, `7`, `30`, défaut `7` ; jours locaux par fuseau.
2. `Ratio(num, den).percent -> int | None`.
3. `available_minutes(rules, time_offs, days, zone)` : intervalles des plages appliquées (`weekday`, `valid_from`, `valid_to`) moins l'union des absences, en minutes.

### `2)` Lecture SQL
> Une requête par bloc, jour local par hôpital.

1. Comptes par statut et source, minutes actives, jours, top 5, liste d'attente (`WAITING`, `OFFERED`).
2. Plages et absences des praticiens actifs avec le fuseau de leur hôpital.

### `3)` Use case et frontières
> `ViewDashboard.execute(actor_id, range)` admin seul.

1. Contexte ajouté aux contrats import-linter ; `uv run lint-imports` vert.

### `4)` Acceptance
> Stories indicateurs et jours/praticiens.

1. Deux `.feature` sur fakes ; indicateurs recalculés sur PostgreSQL ; propriétés Hypothesis des minutes.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | une absence couvrant une plage donne 0 minute ; hors plage, rien n'est retiré |
| 2 | chaque indicateur égal à sa définition recalculée en test |
| 3 | `uv run lint-imports` vert |
| 4 | `uv run pytest tests/use_cases/reporting tests/integration/test_dashboard_postgres.py` vert |
