---
status: pending
---

# Instruction: Écrans RDV de la console
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/web/
│   ├── urls.py                                                 ✏️  `console/appointments/…` avant la route `<slug>`
│   ├── views/console_appointments.py                           ✅  liste, export, fiche, actions, déplacement, assistant
│   ├── presenters/console.py                                   ✏️  entrée « Rendez-vous » dans `_SECTIONS`
│   ├── presenters/console_appointments.py                      ✅  filtres, lignes, fiche, `csv_cell`, assistant
│   └── templates/console/{appointments.html,appointment.html,appointment_cancel.html,book.html} ✅
└── tests/
    ├── presenters/test_console_appointments_presenters.py       ✅  filtres par défaut, fuseau, `csv_cell`, actions
    └── api/test_console_appointment_pages.py                    ✅  pages, export CSV, actions, assistant
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | admin connecté, RDV de deux hôpitaux | prêt | browser |
| Happy path | filtres combinés puis page 2 | lignes filtrées, filtres gardés dans les liens, total, fuseau par ligne | browser |
| Happy path | « Exporter en CSV » | `text/csv` de tout l'ensemble filtré, sans nom ni motif, `'=` préfixé | browser |
| Happy path | fiche → Arrivé, Absent, Annuler avec motif, Déplacer sur la bande de la semaine | statut et notice ; erreurs en ligne | browser |
| Happy path | assistant : patient par nom → type non réservable en ligne → praticien → créneau → salle → confirmer | RDV `STAFF` créé, fiche affichée | browser |
| Edge case | `invalid_transition`, `conflict`, `no_room_available`, `outside_availability` | message en ligne, statut HTTP du code | browser |
| Edge case | praticien sur `/console/appointments/` | 403 | browser |
| Teardown | base vidée | baseline | browser |

## Wireframe
```txt
┌──────────────────────────────────────────────────┐
│ (1) Nav console : … · Rendez-vous · Journal ·     │
│     Réglages · Tableau de bord                    │
├──────────────────────────────────────────────────┤
│ (2) Rendez-vous — heures dans le fuseau de        │
│     l'hôpital de chaque RDV, nommé                │
│     [Réserver pour un patient] [Exporter en CSV]  │
│ (3) <search> Du [ ] Au [ ] Département [▾]        │
│     Praticien [▾] Statut [▾] Source [▾] [Filtrer] │
│ (4) N résultats · page X sur Y                    │
│   ┌──────────────────────────────────────────────┐│
│   │ Début (fuseau) · Patient · Praticien ·        ││
│   │ Département · Type · Statut · Source · Salle  ││
│   │ [Ouvrir]                                      ││
│   └──────────────────────────────────────────────┘│
│ (5) [◀ Précédent] [Suivant ▶]                     │
├──────────────────────────────────────────────────┤
│ (6) Fiche RDV : détails, statut                    │
│     [Arrivé] [Terminé] [Absent] [Annuler]          │
│     Déplacer : bande de la semaine [◀][▶]          │
├──────────────────────────────────────────────────┤
│ (7) Réserver : 1 Patient [nom ou email][Chercher] │
│     2 Type [▾] 3 Praticien [▾] 4 Créneaux semaine │
│     5 Salle [▾ facultative] [Réserver]            │
└──────────────────────────────────────────────────┘
```
1. Nav : sections console, la courante marquée.
2. Titre, note de fuseau, accès à l'assistant et à l'export.
3. Filtres GET combinables ; inutilisables → défaut.
4. Tableau défilant avec légende, 20 lignes.
5. Pagination qui garde les filtres.
6. Fiche : seules les actions permises (`clinician_actions`) ; bande `_week_strip.html` réutilisée.
7. Assistant en étapes GET, la dernière en POST ; pas de « premier disponible ».

## Tasks to do
### `1)` Liste et export
> Filtres, pagination, CSV en streaming.

1. Vue liste : `ListAllAppointments`, presenter calqué sur `console_list` (liste d'attente).
2. Export : `ExportAppointments`, `StreamingHttpResponse`, `csv_cell` sur chaque cellule.

### `2)` Fiche et actions
> Mêmes use cases que l'espace praticien.

1. Fiche admin, statuts, annulation avec motif, déplacement via `FindFreeWeek(for_patient=False)` ; erreurs `_INLINE`.

### `3)` Assistant de réservation
> `BookForPatient` avec praticien et salle.

1. `PatientLookup.active_patients`, types actifs, praticiens du département, semaine libre, salles actives.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | CSV = toutes les lignes filtrées, colonnes §13, UTC ISO 8601, cellule `=…` préfixée |
| 2 | chaque action change le statut ou affiche son refus en ligne |
| 3 | un type non réservable en ligne est réservé en `STAFF` |
| all | `uv run pytest tests/presenters tests/api` vert ; axe sans violation à 375 et 1440 px (phase 8) |
