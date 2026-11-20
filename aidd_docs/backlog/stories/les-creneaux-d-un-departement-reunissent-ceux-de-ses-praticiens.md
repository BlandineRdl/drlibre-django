---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.1, §14)
parent: aidd_docs/backlog/epics/les-praticiens-publient-leurs-disponibilites-et-les-creneaux-libres-en-decoulent.md
depends_on: aidd_docs/backlog/stories/les-plages-du-praticien-donnent-ses-creneaux-libres.md
---

# Story: Les créneaux d'un département réunissent ceux de ses praticiens
**As** patient connecté
**I want** obtenir les créneaux libres d'un type sans nommer de praticien
**So that** je voie tous les horaires possibles du département

## Acceptance
- Sans praticien nommé, `GET /slots` renvoie l'union des créneaux libres de chaque praticien actif du département du type, une seule entrée par début.
- Un praticien inactif n'y apporte aucun créneau.
- Les règles du calcul par praticien, dont le plafond de 31 jours, s'appliquent à l'identique.
