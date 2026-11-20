---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§6.2, §6.4, §4, §17)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
depends_on: aidd_docs/backlog/stories/un-visiteur-cherche-un-praticien-un-hopital-ou-une-specialite.md
---

# Story: Chaque résultat montre ses prochaines disponibilités
**As** visiteur
**I want** voir sur chaque résultat ses prochains créneaux libres
**So that** je choisisse sans ouvrir chaque fiche

## Acceptance
- Un praticien montre ses 3 prochains débuts libres ; un hôpital, son premier créneau libre et le nombre de praticiens qui ont un créneau libre dans l'horizon ; une spécialité, son premier créneau libre parmi tous ses praticiens.
- Sans filtre de type, les créneaux sont ceux du type actif réservable en ligne le plus court du département du praticien, et le résultat nomme ce type.
- Les créneaux sont cherchés de maintenant plus 120 minutes jusqu'à 90 jours devant.
- Un résultat sans créneau dans l'horizon reste listé, après ceux qui en ont, avec le texte « Aucune disponibilité dans les 90 prochains jours ».
- Par défaut, les résultats sont triés par disponibilité la plus proche.
- Les créneaux montrés sont exactement ceux que la réservation accepterait au moment où la liste est construite.
- Les heures sont dans le fuseau de l'hôpital, que la page nomme.
- Sur la seed de charge (option « taille » du script de seed : 10 hôpitaux, 200 praticiens, 5k patients, 50k RDV), la recherche répond sous 200 ms au p95 du scénario Locust.
