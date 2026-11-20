---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.1, §9, §3.1)
parent: aidd_docs/backlog/epics/les-praticiens-publient-leurs-disponibilites-et-les-creneaux-libres-en-decoulent.md
depends_on:
  - aidd_docs/backlog/stories/le-praticien-declare-ses-absences.md
  - aidd_docs/backlog/stories/les-plages-du-praticien-donnent-ses-creneaux-libres.md
---

# Story: Les absences et les RDV actifs retirent des créneaux
**As** praticien
**I want** que mes absences et mes RDV actifs retirent les créneaux qu'ils chevauchent
**So that** aucun créneau proposé ne soit déjà occupé

## Acceptance
- Un créneau qui chevauche une absence du praticien n'est pas renvoyé.
- Un créneau qui chevauche un RDV actif du praticien, prolongé à sa fin du buffer du type demandé, n'est pas renvoyé.
- Un RDV `CANCELLED` ou `NO_SHOW` ne retire aucun créneau.
- Une absence créée ou supprimée change les créneaux renvoyés dès la réponse qui l'enregistre ; un RDV qui devient actif ou cesse de l'être aussi.
