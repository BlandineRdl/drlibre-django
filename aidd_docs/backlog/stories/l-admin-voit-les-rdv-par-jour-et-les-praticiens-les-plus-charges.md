---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Dashboard, §13)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
depends_on: aidd_docs/backlog/stories/l-admin-suit-les-indicateurs-du-tableau-de-bord.md
---

# Story: L'admin voit les RDV par jour et les praticiens les plus chargés
**As** admin
**I want** la répartition des RDV par jour et les praticiens les plus chargés sur la période choisie
**So that** je repère les pics d'activité et la charge de chacun

## Acceptance
- Un histogramme montre, pour chaque jour de la période, le nombre de RDV non annulés qui y commencent, dans le fuseau de l'hôpital de chaque RDV.
- Les 5 praticiens les plus chargés sont classés par nombre de RDV non annulés sur la période.
- L'histogramme et le classement suivent la période choisie pour les indicateurs.
