---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Appointments, §5.2, §5.3, §5.6, §11, §14)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
depends_on: aidd_docs/backlog/stories/l-admin-liste-les-rdv-de-tous-les-hopitaux.md
---

# Story: L'admin déplace n'importe quel RDV
**As** admin
**I want** déplacer un RDV de n'importe quel praticien
**So that** je règle un changement de planning pour le patient

## Acceptance
- Seul un RDV `BOOKED` peut être déplacé ; sinon `invalid_transition` avec le statut courant.
- Le praticien et le type restent ceux du RDV ; le nouveau début doit être un de leurs créneaux libres (`outside_availability`).
- Un chevauchement avec un RDV actif du patient ou de la salle renvoie `conflict`, le RDV déplacé étant ignoré ; les règles réservées aux patients ne s'appliquent pas.
- La salle est réattribuée en préférant la salle courante ; aucune salle libre donne `no_room_available`.
- Le patient reçoit une notification « RDV déplacé » et un email.
- Le déplacement est aussi disponible par `POST /appointments/{id}/reschedule` (§14).
- Le déplacement laisse une entrée d'audit sans donnée personnelle.
