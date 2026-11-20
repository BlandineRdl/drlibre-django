---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Waitlist, §4)
parent: aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
depends_on: aidd_docs/backlog/stories/le-patient-s-inscrit-sur-la-liste-d-attente.md
---

# Story: L'admin suit la liste d'attente
**As** admin
**I want** voir les entrées de la liste d'attente filtrées par statut
**So that** je sache qui attend et depuis quand

## Acceptance
- La liste montre les entrées de tous les hôpitaux, des plus anciennes aux plus récentes, filtrées par statut, par pages de 20 avec le total.
- Un filtre inutilisable dans l'adresse revient à la valeur par défaut au lieu de faire échouer la page.
