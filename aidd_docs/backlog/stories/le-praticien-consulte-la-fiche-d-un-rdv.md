---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §12.3)
parent: aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md
depends_on: aidd_docs/backlog/stories/le-praticien-voit-son-agenda-du-jour.md
---

# Story: Le praticien consulte la fiche d'un RDV
**As** praticien
**I want** ouvrir un de mes RDV depuis l'agenda
**So that** j'aie sous les yeux le patient, le RDV et son historique

## Acceptance
- La fiche montre le nom, le téléphone et l'âge du patient, l'heure, le type, la salle, le motif et le statut.
- L'historique liste les entrées d'audit de ce RDV dans l'ordre chronologique.
- Le RDV d'un autre praticien affiche « Not your appointment » et aucune de ses données.
- Un RDV inexistant donne `not_found`.
