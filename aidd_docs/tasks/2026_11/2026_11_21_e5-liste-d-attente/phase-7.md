---
status: pending
---

# Instruction: Écrans portail et console, API
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/
│   ├── api/waitlist.py                                          ✅  `POST /waitlist`, `POST /waitlist/{id}/accept`
│   ├── api/__init__.py                                          ✏️  mounts the waitlist router
│   └── web/
│       ├── urls.py                                              ✏️  `portal/waitlist`, `portal/waitlist/<id>/accept`; `console/waitlist/`, `new`, `<id>/offer`, `<id>/accept` before the slug catch-all
│       ├── views/portal.py                                      ✏️  `waitlist`, `accept_offer`
│       ├── views/console_waitlist.py                            ✅  `list_entries`, `add_entry`, `offer`, `accept`
│       ├── presenters/waitlist.py                               ✅  `WAITLIST_STATUS_LABELS`, entry cards, admin rows, status filter, join forms
│       ├── presenters/console.py                                ✏️  « Liste d'attente » section
│       └── templates/
│           ├── _nav.html                                        ✏️  patient link « Liste d'attente »
│           ├── portal/waitlist.html                             ✅
│           └── console/{waitlist.html,waitlist_form.html}       ✅
├── aidd_docs/rules/06-design-patterns/6-domain-errors.md        ✏️  waitlist pages and their inline codes
└── tests/
    ├── presenters/test_waitlist_presenters.py                   ✅
    ├── api/test_waitlist_endpoints.py                           ✅
    └── api/test_waitlist_pages.py                               ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `bookable()` world, stored passwordless patient, admin, clinician sessions | ready | system |
| Happy path | patient GET then POST `/portal/waitlist` | form with online types and active clinicians; redirect `?done=joined`; entry listed `En attente` | browser |
| Happy path | patient with an `OFFERED` entry | card shows the offered time with zone and « Accepter »; POST accept redirects to appointments with the new RDV | browser |
| Edge case | refused join or accept | form re-rendered with field errors or the refusal text (rules, conflict, status) and its HTTP status | browser |
| Happy path | admin `/console/waitlist/?status=WAITING`, « Proposer un créneau », « Accepter pour le patient », `/console/waitlist/new` | rows oldest first, 20 per page with total; actions redirect with a notice | browser |
| Edge case | `?status=bogus`, `?page=x` | all statuses, page 1 | browser |
| Happy path | `POST /api/v1/waitlist` as patient and as admin with `patient_email`; `POST /waitlist/{id}/accept` | 201 with the entry; 201 with the appointment | api |
| Edge case | anonymous; clinician; patient naming `patient_email`; unknown field; conflict on accept | 401 `unauthenticated`; 403 `forbidden`; 403; 400 `invalid_input`; 409 with resources | api |
| Teardown | test database flushed | baseline | system |

## Wireframe
```txt
┌──────────────────────────────────────────────┐
│ (1) Header · nav patient (… Liste d'attente)  │
├──────────────────────────────────────────────┤
│ (2) Notice « Inscription enregistrée »        │
│ (3) Mes inscriptions                          │
│  ┌──────────────────────────────────────────┐ │
│  │ (4) Type · praticien · du … au …         │ │
│  │     Statut : Créneau proposé             │ │
│  │     Proposé : lun. 23/11 09:00, fuseau … │ │
│  │     [ Accepter ]                         │ │
│  └──────────────────────────────────────────┘ │
│ (5) S'inscrire                                │
│     Type [select] · Praticien (facultatif)    │
│     Du [date] · Au [date] · [ S'inscrire ]    │
└──────────────────────────────────────────────┘
```
1. Header and patient nav, the new link marked current.
2. Status notice after join or accept, or the refusal in `role="alert"`.
3. Own entries, newest first; empty state when none.
4. Entry card; the offered line and button only when the domain allows acceptance.
5. Join form from `_form.html`, errors linked to fields.

```txt
┌──────────────────────────────────────────────┐
│ (1) Section nav console (… Liste d'attente)   │
├──────────────────────────────────────────────┤
│ (2) Statut [Tous ▾] [ Filtrer ] · [ Inscrire ]│
│ (3) 42 résultat(s) · page 1 sur 3             │
│ (4) Inscrite le · Patient · Type · Praticien  │
│     · Fenêtre · Statut · Proposé · Actions    │
│     … [ Proposer un créneau ] / [ Accepter ]  │
│ (5) ‹ Page précédente · Page suivante ›       │
└──────────────────────────────────────────────┘
```
1. Console section nav.
2. GET filter form on status and link to the add form.
3. Total and page summary.
4. Table rows oldest first; action per status as POST buttons.
5. Pagination keeping the status filter.

## Tasks to do
### `1)` Presenters
> ViewModels only, no rule.

1. Status labels (`En attente`, `Créneau proposé`, `RDV obtenu`, `Expirée`), window and offered time with the hospital zone, accept flag from the domain, status filter parsing with fallback, join form specs and choices from `WaitlistQueries`.

### `2)` Portal pages
> §8 Waitlist.

1. `waitlist` GET/POST and `accept_offer` POST under `@require_role(Role.PATIENT)`, `_private`, inline refusals per plan Decisions; nav link.

### `3)` Console pages
> §10 Waitlist.

1. `list_entries`, `add_entry` (patient email, any active type), `offer`, `accept` under `@require_role(Role.ADMIN)`; routes before `console/<slug:slug>/`; section entry; rule `6-domain-errors` text.

### `4)` API
> §14 rows for the waitlist.

1. Router with `auth=None`, `identity_of` else `unauthenticated`, schemas `extra="forbid"`, use cases decide the role.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | presenter tests on each status; no time without its zone |
| 2 | every portal page renders for a passwordless patient; accept shown only when allowed |
| 3 | bad filters fall back; non-admin gets 403 |
| 4 | API refusals carry the same codes and details as the use cases; API bullets of the Stories map to test names |
