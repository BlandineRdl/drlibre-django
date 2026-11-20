---
status: done
---

# Instruction: Organisation referential and its admin screens
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/organisation/
│   ├── domain/
│   │   ├── hospital.py                    ✅  §3.1 fields, IANA time zone, optional lat/long
│   │   ├── specialty.py                   ✅
│   │   ├── department.py                  ✅  belongs to one hospital
│   │   ├── room.py                        ✅  capacity >= 1, equipment tuple
│   │   ├── appointment_type.py            ✅  duration >= 1, buffer >= 0, #RRGGBB, needs room, online
│   │   └── dependents.py                  ✅  Dependents value object listed by has_dependents
│   ├── application/
│   │   ├── ports/inbound.py               ✅  Save*/Delete* per entity, ReferenceQueries reads
│   │   ├── ports/outbound.py              ✅  repositories, ScheduleDependents
│   │   └── use_cases/{save,delete}_{hospital,specialty,department,room,appointment_type}.py ✅
│   └── infrastructure/
│       ├── django/{apps,models}.py        ✅  unique codes, FK PROTECT
│       ├── django/migrations/0001_initial.py ✅
│       ├── repositories.py                ✅
│       ├── queries.py                     ✅  DjangoReferenceQueries: search, 20 per page, total
│       └── schedule_dependents.py         ✅  NoScheduleYet null adapter
├── src/drlibre/interfaces/web/
│   ├── views/console_reference.py         ✅  list, create, edit, confirm delete per entity
│   ├── presenters/reference.py            ✅  list and form ViewModels, refusal lists
│   └── templates/console/{list,form,confirm_delete}.html ✅  shared, entity-parametrised
├── config/settings.py                     ✏️  organisation app
├── pyproject.toml                         ✏️  import-linter containers
├── src/drlibre/bootstrap/container.py     ✏️
└── tests/
    ├── features/organisation/{hospitals,specialties,departments,rooms,appointment_types,deletion_refusals}.feature ✅
    ├── use_cases/organisation/test_*.py   ✅
    ├── fakes/organisation.py              ✅  one in-memory repository per port, schedule dependents
    ├── contracts/test_organisation_repositories.py ✅
    ├── integration/test_reference_queries_postgres.py ✅
    ├── presenters/test_reference_presenters.py ✅
    └── api/test_console_reference.py      ✅  integration: admin CRUD, clinician 403
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | signed-in admin, empty referential | console reachable | browser |
| Happy path | create hospital → department → room → type, specialty | each listed, audited with ids and changed field names | browser |
| Happy path | list 25 hospitals, search "nord" | 20 rows page 1, total 25, search filters on name or code | browser |
| Edge case | duplicate code, capacity 0, duration 0, buffer -1, bad colour, bad time zone | `invalid_input` on the field, focus there | browser |
| Edge case | `?page=abc` or `?page=999` | falls back to page 1 / empty state, no error | browser |
| Edge case | delete hospital with departments | `has_dependents` listing the departments | browser |
| Edge case | delete department with rooms or types | refused, listing them | browser |
| Edge case | delete room or type with schedule dependents (fake) | refused, listing them | system |
| Edge case | audit log fails during save | nothing saved | system |
| Edge case | edit an unknown id | 404 page | browser |
| Teardown | flush DB | baseline restored | system |

## Wireframe
```txt
┌───────────────────────────────────────────────────┐
│ (1) Header: DrLibre · console nav · Déconnexion    │
├───────────────────────────────────────────────────┤
│ (2) Hôpitaux                       (3) [ Ajouter ] │
│ (4) Rechercher [_____________] [ Rechercher ]      │
│ (5) ┌───────┬──────┬─────────┬───────┬─────────┐   │
│     │ Nom   │ Code │ Ville   │ Fuseau│ Actif   │   │
│     │ ...   │ ...  │ ...     │ ...   │ Oui/Non │   │
│     └───────┴──────┴─────────┴───────┴─────────┘   │
│ (6) 25 résultats · ‹ Précédent  1/2  Suivant ›     │
└───────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────┐
│ (7) Supprimer « Hôpital Nord » ?                   │
│ (8) Refus : ces départements en dépendent : ...    │
│ (9) [ Supprimer ]  [ Annuler ]                     │
└───────────────────────────────────────────────────┘
```
1. Header with console nav: hospitals, specialties, departments, rooms, types, users, clinicians.
2. Page title per entity.
3. Create link.
4. Search on name or code, GET form.
5. Table with caption; active shown as text; empty state when no rows.
6. Total and pagination, 20 per page.
7. Delete confirmation page.
8. Refusal listing dependents, role=alert.
9. Confirm (POST) or cancel.

## Tasks to do
### `1)` Domain entities and validation
> Each record validates its own fields per §3.1.

1. Five entities with named constructors raising `invalid_input` with field messages.

### `2)` Write use cases with dependents
> Save and delete run in one unit of work with their audit entry.

1. `Save<X>UseCase`: unique code check, audit `<entity>.created` / `.updated` with changed field names.
2. `Delete<X>UseCase`: dependents per §10 table (hospital → departments; department → clinicians, rooms, types; room, type → schedule dependents), `has_dependents` details listing ids and labels.
3. Models, repositories, null `ScheduleDependents` adapter, fakes, contracts.

### `3)` Read queries
> Lists stay fast and paginated.

1. `DjangoReferenceQueries` with search on name or code, 20 rows, total, safe fallback for bad page values.

### `4)` Console screens
> The admin manages each entity from its list.

1. Shared list, form and confirm-delete templates; presenters per entity; hospital time zone shown.
2. Department form selects hospital; room and type forms select department.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | invalid values rejected with field messages in BDD scenarios |
| 2 | `deletion_refusals.feature` green for hospital, department, room, type; failing audit leaves no record |
| 3 | integration test: 25 rows → page sizes 20 and 5, total 25, search narrows |
| 4 | admin creates and edits each entity through the client; clinician gets 403 |
