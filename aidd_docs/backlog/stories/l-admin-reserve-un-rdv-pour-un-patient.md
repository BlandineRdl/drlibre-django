---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Appointments, §5.2, §5.3, §5.4, §11, §14)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
depends_on: aidd_docs/backlog/stories/l-admin-liste-les-rdv-de-tous-les-hopitaux.md
---

# Story: L'admin réserve un RDV pour un patient
**As** admin
**I want** réserver pour un patient actif, avec n'importe quel praticien
**So that** j'aide un patient qui ne peut pas réserver lui-même

## Acceptance
- L'admin choisit le patient par son nom ou son email, parmi les patients actifs.
- L'assistant enchaîne type, praticien et créneau ; il ne propose pas « premier disponible » et inclut les types non réservables en ligne.
- L'admin peut choisir une salle active ; sinon un type qui exige une salle reçoit la salle par défaut du praticien si libre, puis la première salle libre du département, sinon `no_room_available`.
- Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou de la salle renvoient `conflict`.
- Le délai de 120 minutes et la limite de 3 réservations en ligne ne s'appliquent pas.
- Le RDV est créé `BOOKED` avec la source `STAFF` ; le patient reçoit une notification « RDV réservé » et un email.
- La même réservation est disponible par `POST /appointments`, qui exige un praticien pour l'admin (§14).
- La réservation laisse une entrée d'audit sans donnée personnelle.
