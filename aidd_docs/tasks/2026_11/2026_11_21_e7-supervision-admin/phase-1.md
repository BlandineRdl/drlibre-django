---
status: done
---

# Instruction: L'admin agit sur n'importe quel RDV
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/booking/
│   ├── application/use_cases/actor_scope.py                    ✅  `ActorScope`, `actor_scope`, `scoped_appointment`
│   ├── application/use_cases/own_clinician_appointment.py      ✏️  gardes réduites au praticien, `own_appointment_of` remplacé
│   ├── application/use_cases/cancel_appointment.py             ✏️  portée d'acteur, 24 h pour le patient seul
│   ├── application/use_cases/reschedule_appointment.py         ✏️  portée d'acteur, admin en règles du personnel
│   ├── application/use_cases/status_change.py                  ✏️  praticien ou admin
│   ├── application/use_cases/book_for_patient.py               ✏️  admin nomme le praticien
│   ├── application/use_cases/book_appointment_as_caller.py     ✏️  admin routé vers `BookForPatient`
│   └── application/use_cases/write_clinical_notes.py           ✏️  admin toujours `forbidden`
├── src/drlibre/bootstrap/container.py                          ✏️  `Staff` injecté là où la portée en a besoin
└── tests/
    ├── features/booking/{l_admin_annule_ou_change_le_statut_de_n_importe_quel_rdv,l_admin_deplace_n_importe_quel_rdv,l_admin_reserve_un_rdv_pour_un_patient}.feature ✅
    ├── use_cases/booking/test_l_admin_{annule_ou_change_le_statut_de_n_importe_quel_rdv,deplace_n_importe_quel_rdv,reserve_un_rdv_pour_un_patient}.py ✅
    └── use_cases/booking/steps_admin.py                         ✅  admin agit, réserve, nomme salle et praticien
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | admin, deux praticiens de deux hôpitaux, patient, RDV `BOOKED` et `CHECKED_IN` | prêt | system |
| Happy path | admin marque arrivé, terminé, absent un RDV d'un autre hôpital | statut changé, audit `{from, to}`, aucune notification | system |
| Edge case | admin passe `COMPLETED` → `CHECKED_IN` | `invalid_transition` avec le statut courant | system |
| Happy path | admin annule dans les 24 h avec motif | `CANCELLED`, heure et motif, « RDV annulé » et email, offre liste d'attente, audit sans motif | system |
| Edge case | annulation sans motif | `invalid_input` | system |
| Happy path | admin déplace vers un créneau libre dans 30 min | déplacé, salle courante préférée, « RDV déplacé » et email | system |
| Edge case | hors créneau, chevauchement patient, aucune salle, depuis `CHECKED_IN` | `outside_availability`, `conflict`, `no_room_available`, `invalid_transition` | system |
| Happy path | admin réserve un type non réservable en ligne dans 30 min pour un patient ayant 3 réservations en ligne | `BOOKED`, source `STAFF`, « RDV réservé » et email, audit sans donnée personnelle | system |
| Edge case | sans praticien, patient inactif, salle d'un autre département, salle occupée | `invalid_input` `clinician`, `forbidden`, `not_found`, `conflict` | system |
| Edge case | aucune salle nommée : salle par défaut libre, puis occupée, puis toutes occupées | salle par défaut, première salle libre du département, `no_room_available` | system |
| Edge case | chevauchement d'un RDV actif du praticien, puis du patient | `conflict` | system |
| Edge case | début hors créneau libre | `outside_availability` | system |
| Regression | patient et praticien E4/E6 | scénarios inchangés et verts | system |
| Teardown | fakes jetés | baseline | system |

## Tasks to do
### `1)` Portée d'acteur
> Une garde pour patient, praticien et admin.

1. `actor_scope(directory, staff, actor_id)` : profil → `CLINICIAN`, `staff.is_admin` → `ADMIN`, sinon `PATIENT`.
2. `scoped_appointment(scope, appointments, id)` : admin → tout RDV ou `not_found` ; praticien → `own_clinician_appointment` ; patient → `own_appointment`.
3. Supprimer `own_appointment_of` ; `locked_clinician_appointment` prend la portée.

### `2)` Actions admin
> Règles du personnel sur tout RDV.

1. Cancel et reschedule : portée, 24 h et règles patient seulement pour `PATIENT`.
2. `StatusChange` : praticien ou admin ; notes : admin `forbidden`.
3. `BookForPatient` : admin → `clinician_id` requis (`invalid_input`), sinon règle praticien inchangée ; `BookAppointmentAsCaller` route l'admin.

### `3)` Acceptance
> Stories annule/statut, déplace, réserve (puces API en phase 4, liste d'attente vérifiée par l'offre).

1. Trois `.feature` et `steps_admin.py` sur fakes ; « a signed-in admin » réutilisé de `steps_waitlist.py`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | un patient lit toujours son seul RDV, un praticien le sien, l'admin tout RDV |
| 2 | admin annule dans les 24 h, déplace dans les 120 min, réserve en `STAFF` ; notes refusées |
| 3 | `uv run pytest tests/use_cases -m "not integration"` vert |
