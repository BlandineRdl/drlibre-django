---
status: done
---

# Instruction: Users and clinician profiles
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/identity/
│   ├── application/
│   │   ├── ports/inbound.py               ✅  extends phase 2-3: SaveUser, DeleteUser, UserQueries, StaffLookup
│   │   ├── ports/outbound.py              ✅  extends phase 2-3: UpcomingAppointments, AuditActors
│   │   └── use_cases/{save_user,delete_user}.py ✅
│   └── infrastructure/
│       ├── queries.py                     ✅  DjangoUserQueries: search name or email, 20 per page
│       ├── upcoming_appointments.py       ✅  NoAppointmentsYet null adapter
│       └── audit_actors.py                ✅  DjangoAuditActors over the audit table
├── src/drlibre/organisation/
│   ├── domain/clinician_profile.py        ✅  weight >= 1 default 1, default room of the department
│   ├── application/
│   │   ├── ports/outbound.py              ✅  extends phase 2-3: ClinicianProfiles, StaffDirectory
│   │   └── use_cases/{attach_clinician_profile,edit_clinician_profile}.py ✅
│   │   └── use_cases/{delete_department,delete_specialty,delete_room,save_room}.py ✅  extends phase 2-3: clinician dependents
│   └── infrastructure/
│       ├── django/models.py               ✅  extends phase 2-3: ClinicianProfileRecord
│       ├── django/migrations/0002_clinician_profile.py ✅
│       ├── repositories.py                ✅  extends phase 3
│       └── staff_directory.py             ✅  calls identity StaffLookup
├── src/drlibre/interfaces/web/
│   ├── views/console_users.py             ✅
│   ├── views/console_clinicians.py        ✅
│   ├── presenters/{users,clinicians}.py   ✅
│   └── templates/console/{users,clinicians}/*.html ✅
├── src/drlibre/bootstrap/container.py     ✏️
├── pyproject.toml                         ✏️  forbidden contract organisation ↔ identity inner layers
└── tests/
    ├── features/identity/manage_users.feature ✅
    ├── features/organisation/clinician_profiles.feature ✅
    ├── features/organisation/deletion_refusals.feature ✅  extends phase 2-3: clinician-based refusals
    ├── use_cases/{identity,organisation}/test_*.py ✅
    ├── fakes/{upcoming_appointments,audit_actors,staff_directory}.py ✅
    ├── contracts/test_{audit_actors,clinician_profiles}.py ✅
    └── api/test_console_users.py          ✅  integration
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | signed-in admin, referential from phase 3 | ready | browser |
| Happy path | create user `Ana@Example.org`, clinician, temporary password | stored `ana@example.org`, `must_change_password`, audited without email | browser |
| Happy path | search users by part of name or email | matching rows, 20 per page | browser |
| Happy path | attach profile: department, specialty, title, bio, default room, weight empty | profile with weight 1, audited | browser |
| Edge case | duplicate email in any case | `invalid_input` on email | browser |
| Edge case | admin deactivates self or changes own role | refused | browser |
| Edge case | deactivate a signed-in user | their next request is signed out | system |
| Edge case | deactivate clinician with upcoming active appointments (fake) | refused, listing those appointments | system |
| Edge case | delete own account, or a user who is an audit actor | refused, message invites to deactivate | browser |
| Edge case | attach to inactive, non-clinician or already-profiled user | refused | browser |
| Edge case | default room inactive or from another department; weight 0 | `invalid_input` | browser |
| Edge case | delete department with clinicians, specialty held by one, room used as default | `has_dependents` listing clinicians | browser |
| Edge case | move a default room to another department | `has_dependents` listing clinicians | browser |
| Teardown | flush DB | baseline restored | system |

## Wireframe
```txt
┌───────────────────────────────────────────────────┐
│ (1) Header: DrLibre · console nav · Déconnexion    │
├───────────────────────────────────────────────────┤
│ (2) Utilisateurs                   (3) [ Ajouter ] │
│ (4) Nom ou email [___________] [ Rechercher ]      │
│ (5) ┌──────────┬───────────────┬──────────┬──────┐ │
│     │ Nom      │ Email         │ Rôle     │ Actif│ │
│     └──────────┴───────────────┴──────────┴──────┘ │
│ (6) total · pagination                             │
└───────────────────────────────────────────────────┘
┌───────────────────────────────────────────────────┐
│ (7) Profil praticien de « Dr Ana Bel »             │
│   Département [▼]   Spécialité [▼]                 │
│   Titre [______]    Salle par défaut [▼]           │
│   Bio [___________________]  Poids [ 1 ]           │
│ (8) [ Enregistrer ]                                │
└───────────────────────────────────────────────────┘
```
1. Header with console nav.
2. Users page.
3. Create user with temporary password.
4. Search by name or email.
5. Users table; role and active as text.
6. Total and pagination.
7. Clinician profile form; room choices limited to active rooms of the chosen department, validated on the server.
8. Submit.

## Tasks to do
### `1)` User management
> Admin creates and edits accounts under the §10 and Story rules.

1. `SaveUserUseCase`: lower-case unique email, temporary password hashed, `must_change_password`, self-deactivation and self-role change refused, deactivation deletes sessions, clinician with upcoming active appointments refused with the list.
2. `DeleteUserUseCase`: own account, audit actor, appointments as patient or clinician → refused, inviting deactivation.
3. `DjangoUserQueries`, null `NoAppointmentsYet`, `DjangoAuditActors`; fakes and contracts.

### `2)` Clinician profiles
> Each clinician sits in one department with a specialty and a weight.

1. `ClinicianProfile` entity; attach and edit use cases via `StaffDirectory` port.
2. Extend department, specialty and room delete, and room save, with clinician dependents.
3. Model, migration, repository, adapter calling identity's `StaffLookup`.

### `3)` Console screens
> Users and clinicians pages in the console.

1. Users list, create, edit, confirm delete; clinicians list, attach, edit.
2. Import-linter forbidden contract between the two contexts' domain and application.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `manage_users.feature` green; deactivated user's session rejected in integration |
| 2 | `clinician_profiles.feature` and clinician refusals in `deletion_refusals.feature` green |
| 3 | admin client flow attaches a profile; `uv run lint-imports` green |
