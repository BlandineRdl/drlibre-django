---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.2, §5.3, §6.2, §7.1, §7.5)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
depends_on: aidd_docs/backlog/stories/un-visiteur-reserve-un-creneau-en-validant-un-code-recu-par-email.md
---

# Story: Une réservation qui enfreint une règle est refusée avec son motif
**As** visiteur
**I want** savoir pourquoi ma réservation échoue et voir les créneaux encore libres
**So that** je puisse en choisir un autre sans recommencer

## Acceptance
- Le placement s'arrête au premier échec, dans cet ordre : type inactif, utilisateur praticien inactif ou départements différents (`not_found`) ; RDV actif qui chevauche pour le même praticien ou le même patient (`conflict`, avec les ressources en cause) ; règles de réservation (`rule_violation`, avec les règles enfreintes) ; aucune salle libre pour un type qui en exige (`no_room_available`).
- Les règles sont : début au moins 120 minutes après maintenant (`lead_time_too_short`), moins de 3 réservations en ligne ouvertes pour le patient, à venir, actives, de source `ONLINE` ou `ROUND_ROBIN` (`too_many_open_bookings`), type réservable en ligne (`type_not_bookable_online`), début égal à l'un des créneaux libres (`outside_availability`).
- L'heure de fin n'est jamais acceptée de l'appelant.
- Un créneau pris entre-temps échoue avec un message et la liste des créneaux à jour.
- Avec un code correct mais un placement en échec, le compte est créé et la session ouverte, puis l'échec s'affiche avec les créneaux à jour.
