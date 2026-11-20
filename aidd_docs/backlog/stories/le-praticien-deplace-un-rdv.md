---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §5.1, §5.2, §5.3, §5.6, §11, §14)
parent: aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md
depends_on: aidd_docs/backlog/stories/le-praticien-consulte-la-fiche-d-un-rdv.md
---

# Story: Le praticien déplace un RDV
**As** praticien
**I want** déplacer un de mes RDV depuis un bandeau de la semaine
**So that** le patient soit vu à un autre moment sans nouvelle réservation

## Acceptance
- Seul un RDV `BOOKED` peut être déplacé ; sinon `invalid_transition` avec le statut courant.
- Le bandeau propose les créneaux libres du même praticien pour le même type ; le praticien et le type ne changent pas.
- Un début qui n'est pas un créneau libre renvoie `rule_violation` avec `outside_availability` ; un chevauchement avec un RDV actif du patient ou de la salle renvoie `conflict`, le RDV déplacé étant ignoré.
- Le délai de 120 minutes, la fenêtre de 24 heures et la réservabilité en ligne du type ne s'appliquent pas.
- La salle est réattribuée en préférant la salle courante ; aucune salle libre donne `no_room_available`.
- Le patient reçoit une notification « RDV déplacé » et un email.
- Sur le RDV d'un autre praticien, le déplacement est refusé avec `forbidden`.
- Le déplacement est aussi disponible par `POST /appointments/{id}/reschedule` (§14).
- Le déplacement laisse une entrée d'audit sans donnée personnelle.
