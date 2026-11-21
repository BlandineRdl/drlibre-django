---
status: done
---

# Instruction: Écrans Aujourd'hui, Calendrier et fiche RDV
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/web/
│   ├── urls.py                                                  ✏️  `workspace/`, `workspace/calendar`, `workspace/appointments/<uuid>` (+ `/check-in`, `/complete`, `/no-show`, `/cancel`, `/reschedule`, `/notes`)
│   ├── views/areas.py                                           ✏️  `/workspace/` renders Aujourd'hui
│   ├── views/workspace.py                                       ✅  `Me`, `_me`, today, calendar, appointment and its forms
│   ├── views/workspace_availability.py                          ✏️  import `Me`, `_me` from `workspace.py`
│   ├── presenters/workspace.py                                  ✅  `TodayPage`, `CalendarPage`, `AppointmentPage`, history rows
│   ├── presenters/availability.py                               ✏️  `week_view` cells accept appointments (type name and colour)
│   ├── presenters/portal.py                                     ✏️  extract `week_strip(week, action_url)`, share `STATUS_LABELS`
│   ├── templates/_nav.html                                      ✏️  Aujourd'hui, Calendrier, Patients, Salles, Mes plages, Mes absences
│   ├── templates/_section_nav.html                              ✏️  `aria-label` from context
│   └── templates/workspace/{today,calendar,appointment,cancel}.html ✅
├── static/drlibre.css                                           ✏️  appointment cell with `--type-colour` border, text label
└── tests/
    ├── presenters/test_workspace_presenters.py                  ✅
    └── api/test_workspace_pages.py                              ✅  pages, inline refusals, « Not your appointment », `no-store`
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | clinician session, appointments today in several statuses, a time off this week | ready | browser |
| Happy path | `/workspace/` | today, hospital time zone named, tiles, rows by hour with allowed buttons only | browser |
| Edge case | `?day=abc` | today | browser |
| Happy path | `/workspace/calendar?week=` | 07:00–19:00 by 30 min, active appointments with type name and colour, time off blocks | browser |
| Happy path | appointment page: check in, complete, notes saved, cancel with reason, reschedule from the strip | redirect with status message; history grows | browser |
| Edge case | cancel without reason; reschedule refused; notes > 5000 | form re-rendered with the error tied to the field | browser |
| Edge case | another clinician's appointment | 403 page « Not your appointment », no data | browser |
| Teardown | test client discarded | baseline | browser |

## Wireframe
```txt
┌──────────────────────────────────────────────────┐
│ (1) Nav: Aujourd'hui · Calendrier · Patients ·    │
│     Salles · Mes plages · Mes absences · Sortir   │
├──────────────────────────────────────────────────┤
│ (2) Aujourd'hui — lun. 23 nov. (Europe/Paris)     │
│     [◀ Précédent] [Aujourd'hui] [Suivant ▶]       │
│ (3) Tuiles: RDV 6 · Annulés 1 · Terminés 2 ·      │
│     Absents 1 · Prochain créneau libre 15:30      │
│ (4) 09:00                                         │
│   ┌──────────────────────────────────────────────┐│
│   │ (5) 09:00 Patient · Type · Salle · Statut     ││
│   │     [Arrivé] [Absent] [Annuler] [Ouvrir]      ││
│   └──────────────────────────────────────────────┘│
├──────────────────────────────────────────────────┤
│ (6) Calendrier — semaine du 23 nov.               │
│     [◀] [Cette semaine] [▶]                       │
│     │ lun │ mar │ … │  07:00 → 19:00 / 30 min     │
│     │ Type│ Abs.│   │                             │
├──────────────────────────────────────────────────┤
│ (7) Fiche RDV                                     │
│   Patient · tél · âge · heure · type · salle ·    │
│   motif · statut                                  │
│   (8) [Arrivé] [Terminé] [Absent] [Annuler]       │
│   (9) Notes cliniques [textarea] [Enregistrer]    │
│   (10) Déplacer: bandeau semaine [◀][▶] créneaux  │
│   (11) Historique: heure · action · par qui       │
└──────────────────────────────────────────────────┘
```
1. Nav: clinician links, current page marked `aria-current`.
2. Day heading with hospital time zone and day navigation.
3. Tiles: counts and next free slot.
4. Hour group heading.
5. Appointment row: patient, type, room, status, allowed actions as POST buttons, link to the page.
6. Week grid: appointments in the type colour with the type name, time off blocks.
7. Appointment facts.
8. Allowed status actions; cancel opens its reason form.
9. Notes form, saved on its own.
10. Week strip of free slots of the same type, `?week=` navigation.
11. Audit history in time order.

## Tasks to do
### `1)` Shared workspace view helpers
> One place for `Me`.

1. Move `Me`, `_me`, `_owned`, `_page` to `views/workspace.py`; `workspace_availability.py` imports them.

### `2)` Aujourd'hui
> §9 Today.

1. View `today(request)` with `?day=`; presenter `today_page(day, rows, next_free, tz)` groups by local hour, actions from `clinician_actions`.
2. POST endpoints for check-in, complete, no-show redirect back with a status message.

### `3)` Calendrier
> §9 Calendar.

1. Extend `week_view` cells with appointments (`CellView(kind="appointment", text=type name, colour)`); template sets `style="--type-colour:#RRGGBB"`.

### `4)` Fiche RDV
> §9 Appointment.

1. Page with facts (age from birth date and the hospital-local today), actions, notes form, cancel form, week strip (`week_strip`), history.
2. `DomainError` `forbidden` → 403 page « Not your appointment » in `lang="en"`; `invalid_input`, `invalid_transition`, `rule_violation`, `conflict`, `no_room_available` inline; `Cache-Control: no-store`.

### `5)` Tests
> Presenters by ViewModel, pages through the test client.

1. `test_workspace_presenters.py`, `test_workspace_pages.py`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | availability and time off pages unchanged (existing tests green) |
| 2 | screen bullets of « agenda du jour » and « actions permises » hold |
| 3 | screen bullets of « semaine » hold; colour never the only cue |
| 4 | screen bullets of « fiche », « annule », « déplace », « notes » hold |
| 5 | `uv run pytest tests/presenters tests/api` green |
