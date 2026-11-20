---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Appointments, §4)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
---

# Story: L'admin liste les RDV de tous les hôpitaux
**As** admin
**I want** filtrer les RDV de tous les hôpitaux
**So that** je retrouve ceux sur lesquels intervenir

## Acceptance
- Les filtres portent sur la période, le département, le praticien, le statut et la source, combinables.
- Les RDV les plus récents viennent en premier, 20 par page avec le nombre total.
- Une valeur de filtre ou de page inutilisable dans l'adresse revient au défaut.
- Les heures sont affichées dans le fuseau de l'hôpital de chaque RDV, et la page indique ce fuseau.
