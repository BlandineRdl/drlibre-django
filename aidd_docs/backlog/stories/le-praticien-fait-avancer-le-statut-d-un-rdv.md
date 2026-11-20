---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §5.6, §14)
parent: aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md
depends_on: aidd_docs/backlog/stories/le-praticien-consulte-la-fiche-d-un-rdv.md
---

# Story: Le praticien fait avancer le statut d'un RDV
**As** praticien
**I want** marquer un de mes RDV arrivé, terminé ou absent
**So that** l'agenda et le reporting reflètent ce qui s'est passé

## Acceptance
- Un RDV `BOOKED` peut passer à `CHECKED_IN` ou `NO_SHOW` ; un RDV `CHECKED_IN` à `COMPLETED` ; `COMPLETED`, `CANCELLED` et `NO_SHOW` sont définitifs.
- L'agenda du jour et la fiche ne proposent que les actions permises par le statut courant.
- Une transition interdite renvoie `invalid_transition` avec le statut courant.
- Ces changements ne notifient pas le patient.
- Sur le RDV d'un autre praticien, l'action est refusée avec `forbidden`.
- Les mêmes changements sont disponibles par `POST /appointments/{id}/check-in`, `/complete` et `/no-show` (§14).
- Chaque changement laisse une entrée d'audit avec l'ancien et le nouveau statut, sans donnée personnelle.
