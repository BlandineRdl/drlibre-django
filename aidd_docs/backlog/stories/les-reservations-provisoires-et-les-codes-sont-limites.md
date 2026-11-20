---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§7.1, §7.5, §7.7, §14)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
depends_on: aidd_docs/backlog/stories/un-visiteur-reserve-un-creneau-en-validant-un-code-recu-par-email.md
---

# Story: Les réservations provisoires et les codes sont limités
**As** visiteur
**I want** que le créneau que je tiens ne soit proposé à personne d'autre le temps de valider mon code
**So that** personne ne me le prenne, sans que quiconque puisse accaparer des créneaux

## Acceptance
- Dès sa création, un créneau tenu disparaît de la recherche, des pages publiques et de `GET /slots`, et toute réservation qui le chevauche échoue en `conflict`.
- Un email n'a jamais plus d'une réservation provisoire ouverte à la fois.
- Le créneau redevient libre dès l'heure d'expiration, même avant le passage du job d'expiration ; ce job tourne chaque minute et audite chaque expiration avec le domaine de l'email.
- Si le code n'est jamais saisi, aucun RDV ni compte n'est créé.
- Un code vaut 10 minutes et 5 essais ; au-delà, il n'est plus accepté ; chaque échec est audité avec le domaine de l'email.
- `POST /booking/holds/{id}/resend` envoie un nouveau code, 3 fois par heure et par email au plus.
- Une même adresse réseau crée au plus 20 réservations provisoires et demande au plus 20 codes par heure.
