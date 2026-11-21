---
status: pending
---

# Instruction: `Appointment` : déplacer, annuler, statuts, notes

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/fhir/
│   ├── routers/appointments.py                                    ✏️  `update` : diff → reschedule, cancel, check-in, complete, no-show, notes ; `If-Match`
│   ├── mappers/appointment.py                                     ✏️  transitions FHIR → use case
│   └── registry.py                                                ✏️  `update` déclaré
└── tests/
    ├── features/fhir/un_client_deplace_annule_et_change_le_statut_d_un_rdv_en_fhir.feature  ✅
    └── fhir/test_un_client_deplace_annule_et_change_le_statut_d_un_rdv_en_fhir.py  ✅
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | RDV `BOOKED` d'un patient, entrée d'attente correspondante, praticien, admin | prêt | system |
| Happy path   | patient `PUT` nouveau `start` | 200 `booked` déplacé, salle courante préférée, audit et e-mail de l'écran | api |
| Happy path   | patient `PUT` `cancelled` + `cancelationReason` | 200 `cancelled`, offre envoyée à l'entrée en attente | api |
| Happy path   | praticien du RDV `checked-in`, puis `fulfilled` ; ou `noshow` | 200 ; `NO_SHOW` reconstruit les créneaux | api |
| Happy path   | praticien du RDV change `comment` | notes écrites, audit `{fields: (clinical_notes,)}` | api |
| Edge case    | annulation sans motif | 400 `invalid_input` | api |
| Edge case    | patient à moins de 24 h | 422 `rule_violation` `cancellation_window_closed` | api |
| Edge case    | patient `checked-in` | 403 | api |
| Edge case    | `fulfilled` depuis `booked`, ou retour à `booked` | 409 `invalid_transition`, statut courant dans le détail | api |
| Edge case    | déplacement d'un RDV non `booked`, ou qui change praticien ou type | 409 `invalid_transition` / 400 `invalid_input` | api |
| Edge case    | `If-Match` périmé | 412, rien écrit | api |
| Edge case    | admin `comment` | 403 | api |
| Teardown     | base et Mailpit vidés | baseline | system |

## Tasks to do

### `1)` `update` `Appointment`

> Une seule intention par mise à jour, traduite en use case.

1. Diff : `start` → `RescheduleAppointment` ; `status` `cancelled` + motif → `CancelAppointment` ; `checked-in`/`fulfilled`/`noshow` → `StatusChange` ; `comment` → `WriteClinicalNotes` ; autre statut → `invalid_transition` avec le statut courant.
2. Plusieurs intentions à la fois → `invalid_input`.
3. `If-Match` par `ConditionalWrites` (cible RDV).

### `2)` Scénarios

> Toutes les puces ; refus, audit, notifications et e-mails comparés à l'écran.

1. Noms identiques aux puces.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | chaque transition déclenche le même use case que `POST /api/v1/appointments/{id}/…` |
| 2 | scénarios verts ; e-mails lus dans Mailpit |
