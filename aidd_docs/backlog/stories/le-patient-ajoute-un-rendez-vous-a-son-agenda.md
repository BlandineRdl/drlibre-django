---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§8 Calendar file)
parent: aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md
depends_on: aidd_docs/backlog/stories/le-patient-retrouve-ses-rendez-vous-a-venir-et-passes.md
---

# Story: Le patient ajoute un rendez-vous à son agenda
**As** patient connecté, avec ou sans mot de passe
**I want** télécharger un RDV en fichier calendrier
**So that** il apparaisse dans mon agenda personnel

## Acceptance
- Chaque RDV de la liste, à venir ou passé, se télécharge en événement iCalendar (`.ics`) aux heures de début et de fin du RDV.
- Un patient ne télécharge que ses propres RDV.
