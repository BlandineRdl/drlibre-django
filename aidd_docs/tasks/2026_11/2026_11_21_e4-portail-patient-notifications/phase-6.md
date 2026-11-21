---
status: pending
---

# Instruction: Portail patient web et API d'annulation et de déplacement
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/
│   ├── api/appointments.py                                      ✏️  `POST /appointments/{id}/cancel` `{reason}`, `/reschedule` `{start}`; staff `forbidden`
│   └── web/
│       ├── urls.py                                              ✏️  `/portal/` routes
│       ├── context.py                                           ✏️  patient nav links, unread count
│       ├── views/areas.py                                       ✏️  `/portal/` home from the use cases
│       ├── views/portal.py                                      ✅  appointments, cancel, reschedule, `.ics`, notifications, profile
│       ├── presenters/portal.py                                 ✅  ViewModels: home, agenda rows, cancel form, week strip, notifications, profile form
│       └── templates/
│           ├── _nav.html                                        ✏️  Mes RDV, Notifications (n), Profil
│           ├── areas/home.html                                  ✏️  patient variant or new `portal/home.html`
│           └── portal/{home,appointments,cancel,reschedule,notifications,profile}.html ✅
└── tests/
    ├── features/booking/{le_patient_ajoute_un_rendez_vous_a_son_agenda,le_patient_voit_son_prochain_rendez_vous_des_l_accueil}.feature ✅
    ├── use_cases/booking/test_….py                              ✅
    ├── presenters/test_portal_presenters.py                     ✅
    └── api/{test_portal_pages.py,test_appointment_actions.py}   ✅  ownership, cross-origin refused, API rules equal use case rules
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | patient session with appointments and notifications | ready | browser |
| Happy path | `/portal/` | greeting, next appointment, unread count, « Prendre un RDV » → `/` | browser |
| Happy path | `/portal/appointments` | two lists; « Déplacer »/« Annuler » only where allowed; `.ics` link per row | browser |
| Happy path | cancel with reason; reschedule from the week strip | redirect to list with status message; notification count rises | browser |
| Edge case | cancel without reason | form re-rendered, error tied to the field, focus on it | browser |
| Edge case | reschedule refused | strip re-rendered with the refusal and rules | browser |
| Edge case | `.ics` of another patient | 403 | browser |
| Edge case | appointment under 24 h (stored by the test) | no « Déplacer »/« Annuler »; API gives `cancellation_window_closed` | browser |
| Happy path | `POST /appointments/{id}/cancel`, `/reschedule` | same outcomes as the use cases; end never accepted (`extra="forbid"`) | api |
| Happy path | profile with password vs passwordless | « Mot de passe » link shown vs hidden | browser |
| Teardown | test client discarded | baseline | browser |

## Wireframe
```txt
┌──────────────────────────────────────────────┐
│ (1) Nav: Rechercher · Mon espace · Mes RDV · │
│     Notifications (2) · Profil · Déconnexion │
├──────────────────────────────────────────────┤
│ (2) Accueil /portal/                         │
│   Bonjour · prochain RDV · non lues · [Prendre un RDV]
├──────────────────────────────────────────────┤
│ (3) Mes RDV /portal/appointments             │
│   À venir                                    │
│   ┌────────────────────────────────────────┐ │
│   │ (4) Carte RDV: quand + fuseau · qui ·  │ │
│   │  où · type · statut · motif ·          │ │
│   │  [Déplacer] [Annuler] [.ics]           │ │
│   └────────────────────────────────────────┘ │
│   Passés: cartes sans actions, [.ics]        │
├──────────────────────────────────────────────┤
│ (5) Annuler: rappel du RDV · Motif [____] ·  │
│     [Confirmer l'annulation] [Retour]        │
├──────────────────────────────────────────────┤
│ (6) Déplacer: < semaine > · jours ·          │
│     [créneau] boutons · refus inline         │
├──────────────────────────────────────────────┤
│ (7) Notifications: ● titre · heure ·         │
│     [Marquer comme lu]                       │
├──────────────────────────────────────────────┤
│ (8) Profil: nom, email (lecture) ·           │
│     Téléphone [__] · Naissance [__] ·        │
│     [Enregistrer] · Mot de passe →           │
└──────────────────────────────────────────────┘
```
1. Nav: patient links, unread count in the Notifications label.
2. Home: greeting, next upcoming appointment, unread count, link to the public search.
3. Appointments: upcoming soonest first, past latest first.
4. Card: one appointment with the Story fields; actions only when allowed.
5. Cancel: confirmation with the required reason, error tied to the field.
6. Reschedule: week strip of free slots, same clinician and type; each slot posts its start.
7. Notifications: newest first, unread marked by text and symbol, not colour alone.
8. Profile: editable phone and birth date; password link only for a password holder.
## Tasks to do
### `1)` Portal pages
> Every §8 screen for the patient.

1. Views under `@require_role(Role.PATIENT)` calling container use cases only; presenters build every label, date and allowed action.
2. Cancel: GET confirmation page, POST with reason (`invalid_input` re-renders); reschedule: week strip from `FindFreeSlots(ignoring_appointment)`, `?week=` as the provider page, slot buttons POST `start`; refusals shown inline.
3. `.ics` under `/portal/appointments/<id>.ics` reusing `calendar_file`.
4. Notifications list with « Marquer comme lu » POST; home shows unread count; nav links.

### `2)` Patient actions API
> §14 for the patient.

1. `POST /appointments/{id}/cancel` and `/reschedule`, body `extra="forbid"`, `identity_of` then `require_patient` (staff `forbidden`).

### `3)` Story scenarios and presenters
> Stories « agenda » and « accueil », API and password bullets of the earlier Stories.

1. One scenario per acceptance bullet; presenter tests on ViewModels; page tests for ownership and same-origin.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | every page renders for a passwordless patient; actions shown match `allowed_actions` |
| 2 | API refusals carry the same codes and rules as the use cases |
| 3 | each acceptance bullet of the 8 Stories maps to a scenario name |
