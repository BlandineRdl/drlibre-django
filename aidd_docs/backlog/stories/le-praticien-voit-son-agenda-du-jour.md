---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §4, §14)
parent: aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md
---

# Story: Le praticien voit son agenda du jour
**As** praticien
**I want** voir les RDV d'une journée de mon agenda
**So that** j'organise ma journée

## Acceptance
- L'agenda s'ouvre sur aujourd'hui ; les liens précédent, suivant et aujourd'hui changent de jour ; une date inutilisable dans l'adresse revient à aujourd'hui.
- Les indicateurs montrent le nombre de RDV, les annulés comptés à part, les terminés, les absents et le prochain créneau libre.
- Les RDV sont groupés par heure, chacun avec patient, type, salle et statut.
- Seuls les RDV du praticien connecté apparaissent ; `GET /appointments` ne lui renvoie que les siens.
- Les heures sont affichées dans le fuseau de l'hôpital, et la page indique ce fuseau.
