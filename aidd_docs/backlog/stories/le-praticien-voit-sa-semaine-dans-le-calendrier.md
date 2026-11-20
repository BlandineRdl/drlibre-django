---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §3.1, §4)
parent: aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md
---

# Story: Le praticien voit sa semaine dans le calendrier
**As** praticien
**I want** une grille de ma semaine
**So that** je repère d'un coup d'œil mes RDV et mes absences

## Acceptance
- La grille couvre la semaine de 07:00 à 19:00 par tranches de 30 minutes.
- Les RDV actifs (ni `CANCELLED` ni `NO_SHOW`) apparaissent dans la couleur de leur type ; les RDV annulés ou absents n'apparaissent pas.
- Les absences du praticien apparaissent en blocs.
- Seuls les RDV et absences du praticien connecté apparaissent, aux heures du fuseau de l'hôpital, indiqué sur la page.
