---
status: pending
---

# Instruction: Écrans Patients et Salles
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/web/
│   ├── urls.py                                                  ✏️  `workspace/patients`, `workspace/rooms`
│   ├── views/workspace.py                                       ✏️  patients, rooms
│   ├── presenters/workspace.py                                  ✏️  `PatientsPage`, `RoomsPage`
│   └── templates/workspace/{patients,rooms}.html                ✅
├── static/drlibre.css                                           ✏️  rooms timeline
└── tests/
    ├── presenters/test_workspace_presenters.py                  ✏️
    └── api/test_workspace_pages.py                              ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | clinician with patients, another clinician of the department booking a room | ready | browser |
| Happy path | `/workspace/patients?q=mar` | own matching patients with phone, last and next visit, paged | browser |
| Edge case | no match | empty state with a reset link | browser |
| Happy path | `/workspace/rooms?day=` | active rooms 07:00–19:00, own rows with patient name, others « Occupied », time zone named | browser |
| Edge case | inactive room | absent from the timeline | browser |
| Teardown | test client discarded | baseline | browser |

## Wireframe
```txt
┌──────────────────────────────────────────────┐
│ (1) Nav (as phase 5)                          │
├──────────────────────────────────────────────┤
│ (2) Patients  [Rechercher par nom____] [OK]   │
│ (3) Nom · Téléphone · Dernière · Prochaine    │
│     … 20 per page  [◀ Précédente][Suivante ▶] │
├──────────────────────────────────────────────┤
│ (4) Salles — lun. 23 nov. (Europe/Paris)      │
│     [◀] [Aujourd'hui] [▶]                     │
│ (5) Salle  │07:00│07:30│ … │18:30│            │
│     C101   │     │Dupont│    │Occupied│       │
└──────────────────────────────────────────────┘
```
1. Nav.
2. Name search form.
3. Patients table with pagination.
4. Day heading, time zone, day navigation.
5. Timeline: one row per active room, 30-minute columns, own appointments named, others « Occupied » in `lang="en"`; scrolls inside its own container at 375 px.

## Tasks to do
### `1)` Patients
> §9 Patients.

1. View and presenter over `ClinicianPatients`; dates in the hospital time zone; « — » when none.

### `2)` Salles
> §9 Rooms.

1. View and presenter over `DepartmentRoomsDay`; table with row headers per room and column headers per half hour.

### `3)` Tests
> Presenters by ViewModel, pages through the test client.

1. Extend `test_workspace_presenters.py`, `test_workspace_pages.py`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | every bullet of « retrouve ses patients » holds |
| 2 | every bullet of « occupation des salles » holds; no other clinician's patient name in the HTML |
| 3 | `uv run pytest tests/presenters tests/api` green |
