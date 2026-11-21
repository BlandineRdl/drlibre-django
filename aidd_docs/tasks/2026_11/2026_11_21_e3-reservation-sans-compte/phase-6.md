---
status: pending
---

# Instruction: Parcours de réservation web et API
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/
│   ├── api/booking.py                                     ✅  `POST /booking/holds`, `/booking/holds/{id}/verify` (sets cookie), `/booking/holds/{id}/resend`
│   ├── api/appointments.py                                ✅  `POST /appointments` for the signed-in patient; no clinician = first available; unknown fields refused
│   ├── api/__init__.py                                    ✏️
│   └── web/
│       ├── views/booking.py                               ✅  choose → details → code → confirmation; signed-in patient: choose → confirmation
│       ├── views/errors.py                                ✏️  only if booking refusals need a page outside the forms
│       ├── presenters/booking.py                          ✅  details form, code page (provider, slot, zone, hold expiry), failure with refreshed slots, confirmation
│       ├── presenters/calendar_file.py                    ✅  RFC 5545 `.ics` text
│       ├── templates/booking/{details,code,confirmation,refused}.html ✅
│       └── urls.py                                        ✏️  `/booking/new`, `/booking/holds/<id>`, `/booking/appointments/<id>`, `/booking/appointments/<id>.ics`
└── tests/
    ├── api/test_booking_endpoints.py                      ✅  anonymous hold + verify (code from Mailpit), resend limit, rate limit, `POST /appointments` 401 anonymous, end time refused
    ├── api/test_booking_pages.py                          ✅  cross-origin POST refused; `.ics` only for its patient (`forbidden` otherwise)
    └── presenters/test_booking_presenters.py              ✅  ViewModels and `.ics` content
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | compose stack, demo seed | free slots | system |
| Happy path | anonymous: slot link → details → code from Mailpit → confirmation | appointment shown with zone, `.ics` download, link to `/portal/`, cookie set for 24 h | browser, api |
| Happy path | signed-in patient picks a slot | goes straight to confirmation, same email | browser |
| Edge case | wrong code; resend; expired hold | error tied to the code field with focus; new code; message and refreshed slots | browser |
| Edge case | slot taken meanwhile | message and refreshed slot list, nothing lost | browser |
| Edge case | staff email | generic refusal page | browser |
| Teardown | rollback, Mailpit inbox cleared | baseline | system |

## Wireframe
```txt
┌──────────────────────────────────────────────┐
│ (1) Étapes : Choix · Informations · Code · Confirmation │
├──────────────────────────────────────────────┤
│ (2) Dr Nom · Consultation 20 min              │
│     lun. 23 nov. 9:00 · Fuseau Europe/Paris   │
├──────────────────────────────────────────────┤
│ (3) Nom complet [____]  Naissance [____]      │
│     Email [____]  Téléphone (facultatif) [__] │
│     Motif (facultatif) [__________]           │
│     [x] J'accepte les conditions et la notice │
│     [ Recevoir un code ]                      │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│ (4) Code envoyé à l'adresse saisie            │
│     Créneau tenu jusqu'à 10:42                │
│     Code [______]  [ Réserver ]               │
│     [ Renvoyer un code ]                      │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│ (5) Rendez-vous réservé                       │
│     Dr Nom · hôpital, adresse · date, heure   │
│     [ Ajouter à mon agenda (.ics) ]           │
│     [ Voir mes rendez-vous ]                  │
└──────────────────────────────────────────────┘
```
1. Step indicator in text, current step marked for screen readers.
2. Chosen slot summary; for first available, the department until the hold names the provider.
3. Details form; errors tied to fields, focus on the first invalid one.
4. Code form, hold expiry in the hospital zone, resend; failure re-renders here or shows refreshed slots.
5. Confirmation: appointment, calendar file, link to the patient portal.

## Tasks to do
### `1)` API
> Same flow as the web, no session until the code.

1. Booking and appointments routers; `invalid_input` on unknown fields and on `end`.
2. Verify sets the session cookie like `POST /auth/login`.

### `2)` Web
> Accessible multi-step flow, 375 to 1440 px.

1. Views, presenters, templates, `.ics`; refusals rendered inside the flow with refreshed slots.
2. Signed-in patient shortcut; staff signed in cannot book here (`forbidden`).

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | API tests green against compose; no response before verification contains patient data |
| 2 | presenter tests green; booking pages pass axe in phase 7's journey |
