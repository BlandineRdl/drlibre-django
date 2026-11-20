---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Dashboard, §13, §4)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
---

# Story: L'admin suit les indicateurs du tableau de bord
**As** admin
**I want** les indicateurs d'activité de tous les hôpitaux sur une période
**So that** je mesure l'utilisation, les absences et la part de réservation en ligne

## Acceptance
- La période vaut aujourd'hui, 7 jours ou 30 jours finissant aujourd'hui ; 7 jours par défaut ; une valeur inutilisable dans l'adresse revient au défaut.
- Un RDV compte dans la période si son début tombe dans un de ses jours, comptés dans le fuseau de l'hôpital du RDV.
- RDV : RDV non annulés. Annulations : RDV annulés.
- Utilisation : minutes des RDV actifs dans la période ÷ minutes disponibles, soit les heures des plages des praticiens actifs sur la période moins leurs absences.
- Taux d'absence : `NO_SHOW` ÷ RDV non annulés. Part en ligne : RDV de source `ONLINE` ou `ROUND_ROBIN` ÷ RDV non annulés.
- Taille de la liste d'attente : entrées `WAITING` ou `OFFERED`, quelle que soit la période.
- Un ratio dont le dénominateur est nul affiche « n/a », jamais 0 %.
