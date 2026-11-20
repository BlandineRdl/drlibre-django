---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.4, §7.1, §8, §14)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
depends_on:
  - aidd_docs/backlog/stories/un-visiteur-reserve-un-creneau-en-validant-un-code-recu-par-email.md
  - aidd_docs/backlog/stories/un-visiteur-reserve-le-premier-praticien-disponible.md
---

# Story: Un patient connecté réserve sans ressaisir ses informations
**As** patient connecté
**I want** réserver depuis la recherche ou une page publique sans saisie ni code
**So that** je reprenne un RDV en quelques clics

## Acceptance
- Un patient connecté qui choisit un créneau passe directement de son choix à la confirmation, sans saisie de ses informations ni code.
- Il réserve pour lui-même seulement : son identité vient de la session, et il ne peut nommer ni un autre patient ni une salle.
- `POST /appointments` réserve pour le patient connecté ; sans praticien nommé, il réserve le premier disponible.
- La même page de confirmation et le même email de confirmation suivent la réservation.
