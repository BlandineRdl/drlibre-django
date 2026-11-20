---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.1, §4, §14)
parent: aidd_docs/backlog/epics/les-praticiens-publient-leurs-disponibilites-et-les-creneaux-libres-en-decoulent.md
depends_on: aidd_docs/backlog/stories/le-praticien-gere-ses-plages-hebdomadaires.md
---

# Story: Les plages du praticien donnent ses créneaux libres
**As** praticien
**I want** obtenir les créneaux libres que mes plages ouvrent pour un type de RDV de mon département
**So that** la recherche et chaque réservation reposent sur le même calcul

## Acceptance
- `GET /slots` prend un type, un praticien et une période ; sans session, il répond `unauthenticated`.
- Pour chaque jour local de la période, chaque plage valable ce jour-là propose un début à son heure de début puis à chaque pas, tant que le début plus la durée du type ne dépasse pas sa fin ; chaque créneau dure la durée du type.
- Un créneau qui commence avant la période, finit après elle ou commence dans le passé n'est pas renvoyé.
- Les débuts renvoyés sont uniques et triés par ordre croissant.
- Une période de plus de 31 jours est refusée en `invalid_input`.
- La semaine du changement d'heure, une plage 09:00–12:00 donne toujours un premier créneau à 09:00 heure locale de l'hôpital.
- Une plage créée, modifiée ou supprimée change les créneaux renvoyés dès la réponse qui l'enregistre.
- Les créneaux sont connus jusqu'à 90 jours devant ; cet horizon avance chaque jour sans intervention.
