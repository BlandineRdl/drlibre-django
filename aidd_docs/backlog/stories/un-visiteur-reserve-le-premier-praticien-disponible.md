---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.5, §7.1, §6.6)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
depends_on: aidd_docs/backlog/stories/un-visiteur-reserve-un-creneau-en-validant-un-code-recu-par-email.md
---

# Story: Un visiteur réserve le premier praticien disponible
**As** visiteur
**I want** réserver un créneau d'un département sans choisir de praticien
**So that** j'obtienne le plus tôt possible un RDV du type voulu

## Acceptance
- Au choix du praticien, le parcours propose « premier disponible » dans le département du type ; la page hôpital le propose pour chaque type de RDV.
- Les candidats sont les praticiens actifs du département du type qui ont un créneau libre à ce début.
- Un praticien jamais attribué passe en premier, puis la plus grande valeur de (temps depuis sa dernière attribution × poids) ; à égalité, le plus petit id.
- Le praticien est choisi à la création de la réservation provisoire ; sa date de dernière attribution n'est mise à jour qu'à la réservation.
- Le RDV porte la source `ROUND_ROBIN`.
- Sans candidat, la réservation échoue en `no_clinician_available` et le visiteur en est informé.
