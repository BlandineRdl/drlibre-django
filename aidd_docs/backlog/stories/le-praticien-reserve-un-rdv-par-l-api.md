---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.2, §5.3, §5.4, §11, §14)
parent: aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md
---

# Story: Le praticien réserve un RDV par l'API
**As** praticien
**I want** réserver par `POST /appointments` un RDV dans mon agenda pour un patient actif
**So that** je planifie un suivi sans passer par le patient

## Acceptance
- Le RDV est toujours placé dans l'agenda du praticien connecté ; une requête qui nomme un autre praticien est refusée.
- La requête nomme un patient actif ; la fin est calculée à partir de la durée du type.
- Le type doit être actif et du département du praticien ; sinon `not_found`.
- Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou d'une salle nommée renvoient `conflict`.
- Le délai de 120 minutes, la limite de 3 réservations en ligne et la réservabilité en ligne du type ne s'appliquent pas.
- Une salle nommée doit être active ; sans salle nommée, un type qui en exige une reçoit la salle par défaut si libre, sinon la première salle libre du département, sinon `no_room_available`.
- Le RDV est créé `BOOKED` avec la source `STAFF` ; le patient reçoit une notification « RDV réservé » et un email.
- La réservation laisse une entrée d'audit sans donnée personnelle.
