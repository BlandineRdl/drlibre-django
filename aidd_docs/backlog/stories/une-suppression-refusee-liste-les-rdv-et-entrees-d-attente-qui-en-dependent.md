---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Deleting, §4 has_dependents)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
depends_on: aidd_docs/backlog/stories/l-admin-liste-les-rdv-de-tous-les-hopitaux.md
---

# Story: Une suppression refusée liste les RDV et entrées d'attente qui en dépendent
**As** admin
**I want** que la suppression d'un enregistrement encore utilisé par des RDV ou des entrées d'attente soit refusée
**So that** aucun RDV ni aucune entrée d'attente ne perde son praticien, sa salle, son type ou son patient

## Acceptance
- Une salle qui a des RDV ne peut pas être supprimée.
- Un type de RDV qui a des RDV ou des entrées d'attente ne peut pas être supprimé.
- Un profil praticien qui a des RDV ne peut pas être supprimé.
- Un utilisateur qui a des RDV, comme patient ou comme praticien, ne peut pas être supprimé ; le message invite à le désactiver.
- Chaque refus renvoie `has_dependents` et liste ce qui utilise encore l'enregistrement.
