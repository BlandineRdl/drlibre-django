---
status: pending
---

# Instruction: Liste d'attente et `AppointmentResponse`

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/
│   ├── booking/
│   │   ├── domain/appointment.py                                  ✏️  `Appointment.book(id=None)`
│   │   ├── application/use_cases/placement.py                     ✏️  `place(appointment_id=None)`
│   │   └── application/use_cases/accept_waitlist_offer.py         ✏️  RDV placé avec l'id de l'entrée
│   ├── interop/
│   │   ├── application/ports/inbound.py                           ✏️  `AppointmentResponseReads`
│   │   └── infrastructure/sql_appointment_responses.py            ✅  entrées `BOOKED` : du patient, ou toutes pour l'admin
│   └── interfaces/fhir/
│       ├── routers/appointments.py                                ✏️  `create` `waitlist` → `JoinWaitlist`
│       ├── schemas/appointment_response.py                        ✅
│       ├── routers/appointment_responses.py                       ✅  `create` `accepted` → `AcceptWaitlistOffer`, `read`, `search-type`
│       └── registry.py                                            ✏️  `AppointmentResponse`
└── tests/
    ├── features/booking/le_patient_accepte_un_creneau_propose.feature  ✏️  `Règle §15.3 : le RDV accepté garde l'id de l'entrée`
    ├── use_cases/booking/                                         ✏️  step sur fakes
    ├── features/fhir/un_patient_rejoint_la_liste_d_attente_et_accepte_une_offre_en_fhir.feature  ✅
    ├── fhir/test_un_patient_rejoint_la_liste_d_attente_et_accepte_une_offre_en_fhir.py  ✅
    └── contracts/test_interop_appointment_responses.py            ✅
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | type, praticien, deux patients, un RDV annulable | prêt | system |
| Happy path   | patient `POST /fhir/Appointment` `waitlist`, `serviceType`, `requestedPeriod` | 201 `waitlist`, audit de l'écran | api |
| Happy path   | annulation du RDV d'un autre patient | `Appointment/<entrée>` `proposed` avec début, fin, praticien offerts | api |
| Happy path   | patient `POST /fhir/AppointmentResponse` `accepted` sur son offre | 201 ; `Appointment/<entrée>` devient `booked` ; une seule ressource | api |
| Happy path   | admin inscrit un patient, accepte pour lui | 201 ; source `STAFF` | api |
| Edge case    | praticien inscrit | 403 | api |
| Edge case    | type ou praticien préféré inactif | 404 | api |
| Edge case    | créneau pris entre l'offre et l'acceptation | 409 `conflict`, entrée revenue `waitlist` | api |
| Edge case    | patient accepte l'offre d'un autre | 403 | api |
| Edge case    | entrée expirée | `cancelled` | api |
| Edge case    | `GET /fhir/AppointmentResponse` par un autre patient | ne voit pas celles des autres | api |
| Teardown     | base et Mailpit vidés | baseline | system |

## Tasks to do

### `1)` Une seule ressource

> Le RDV accepté reprend l'id de l'entrée.

1. Id facultatif dans `Appointment.book` et `Placement.place` ; `AcceptWaitlistOffer` le passe.
2. Scénario `Règle §15.3` sur fakes ; `tests/features/booking` vert.

### `2)` Inscription et acceptation FHIR

> Mêmes cas d'usage que `POST /api/v1/waitlist` et `/accept`.

1. `waitlist` : `requestedPeriod` en dates locales du type, praticien préféré facultatif, patient (admin seul pour un autre).
2. `AppointmentResponse` `accepted` → `AcceptWaitlistOffer` ; lecture : entrée `BOOKED`, même id, version de l'entrée.

### `3)` Scénarios

> Toutes les puces de la Story.

1. Noms identiques aux puces.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | après acceptation, `Appointment/<entrée>` est le RDV `booked` |
| 2 | refus identiques à l'API applicative |
| 3 | scénarios verts sur PostgreSQL |
