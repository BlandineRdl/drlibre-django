---
status: done
---

# Instruction: `Appointment` : lecture, recherche, réservation

## Architecture projection

> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/
│   ├── interop/
│   │   ├── domain/rows.py                                         ✏️  `AppointmentRow` (RDV, entrée d'attente, retenue)
│   │   ├── application/ports/inbound.py                           ✏️  `AppointmentReads`
│   │   └── infrastructure/sql_appointments.py                     ✅  union RDV, entrées non réservées, retenues (personnel) ; `patient`, `practitioner`, `location`, `status`, `date`, `service-type`
│   └── interfaces/fhir/
│       ├── schemas/appointment.py                                 ✅  `Appointment`
│       ├── mappers/appointment.py                                 ✅  statuts §15.3, source en extension, `reasonCode.text`, `cancelationReason`, `comment` au praticien du RDV
│       ├── routers/appointments.py                                ✅  `read`, `search-type`, `create` (`proposed` → `BookAppointmentAsCaller`), `_include` patient, praticien, salle
│       └── registry.py                                            ✏️  `Appointment`
└── tests/
    ├── features/fhir/un_client_reserve_et_consulte_des_rdv_en_fhir.feature  ✅
    ├── fhir/test_un_client_reserve_et_consulte_des_rdv_en_fhir.py  ✅  steps PostgreSQL + Mailpit
    └── contracts/test_interop_appointments.py                     ✅  fake vs SQL
```

## Test Scope

| Scenario     | Action                  | Observable outcome   | Actor                           |
| ------------ | ----------------------- | -------------------- | ------------------------------- |
| Setup        | scène réservable (`tests/builders_booking.py`), deux patients, un praticien, un admin | prêt | system |
| Happy path   | jeton patient `POST /fhir/Appointment` `proposed`, `slot` | 201 `booked`, praticien et salle attribués, `end` calculée, source `ONLINE` | api |
| Happy path   | patient sans praticien, début | 201, source `ROUND_ROBIN` | api |
| Happy path   | jeton praticien, patient actif, son agenda | 201 source `STAFF` | api |
| Happy path   | même réservation à l'écran et en FHIR | même entrée d'audit, même notification « RDV réservé », même e-mail | api |
| Happy path   | `GET /fhir/Appointment?patient=…&_include=Appointment:practitioner` | ses RDV + praticiens inclus | api |
| Edge case    | patient nomme un autre patient ou une salle | 403 | api |
| Edge case    | personnel sans praticien | 400 `invalid_input` | api |
| Edge case    | créneau pris, règle violée, salle ou praticien indisponible, type absent | 409 `conflict` (ressources), 422 `rule_violation` (règles), 409 `no_room_available`, 409 `no_clinician_available`, 404 — comme `POST /api/v1/appointments` | api |
| Edge case    | `end` fourni | ignoré, fin calculée | api |
| Edge case    | `reasonCode` à la création | 400 `invalid_input` | api |
| Edge case    | jeton patient lit le RDV d'un autre | 403 ; absent → 404 | api |
| Edge case    | notes cliniques : praticien du RDV, autre praticien, admin, patient | `comment` pour le premier seulement | api |
| Edge case    | retenue ouverte : jeton praticien concerné, admin, patient | `pending` pour les deux premiers seulement | api |
| Teardown     | base et Mailpit vidés | baseline | system |

## Tasks to do

### `1)` Lectures `Appointment`

> Une seule recherche pour les trois sources, limitée au lecteur.

1. SQL union paginée, tri `date`, préfixes de date ; entrée `BOOKED` exclue.
2. Fake et contrat.

### `2)` Ressource et réservation

> Mêmes cas d'usage que `POST /api/v1/appointments`.

1. Mapper statuts §15.3, extension `source`, notes au praticien du RDV.
2. `create` : `proposed` exigé ; `slot` décodé ou `start` + praticien ; `BookAppointmentAsCaller`.
3. Réponse 201 `Location` et ressource lue après écriture.

### `3)` Scénarios

> Toutes les puces de la Story ; refus comparés à l'API applicative.

1. Scenario Outline des refus avec colonne `case` en mots utilisateur.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | contrat fake = SQL ; lecteur borné |
| 2 | statut, praticien, salle, source attendus ; fin calculée |
| 3 | chaque refus FHIR a le même code que l'API applicative dans le même cas |
