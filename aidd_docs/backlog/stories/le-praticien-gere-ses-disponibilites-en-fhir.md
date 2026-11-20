---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.2, §15.4, §9 Availability)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
depends_on: aidd_docs/backlog/stories/un-client-agit-avec-le-jeton-d-un-utilisateur-et-exactement-ses-droits.md
---

# Story: Le praticien gère ses disponibilités en FHIR
**As** client API agissant pour un praticien
**I want** gérer ses plages en `Schedule` et ses absences dans `PractitionerRole.notAvailable`
**So that** son agenda se tienne depuis un outil externe

## Acceptance
- Chaque plage est un `Schedule` dont les acteurs sont le praticien et la salle, l'horizon la période de validité, et le jour, les heures et le pas une extension ; elle est reflétée en lecture seule dans `PractitionerRole.availableTime`.
- Le praticien crée, modifie et supprime ses propres `Schedule` ; ceux d'un autre donnent `forbidden`.
- Les règles sont celles de l'écran : salle active de son département, plages d'un même jour qui se touchent sans se chevaucher, pas de 5 à 240 minutes, fin après début.
- Le praticien ajoute ou retire une absence en mettant à jour `notAvailable` de son propre `PractitionerRole`, sans pouvoir y changer autre chose ; une période identique déjà enregistrée est refusée.
- Une absence n'annule pas les RDV déjà réservés ; les `Slot` reflètent aussitôt chaque changement.
- Chaque écriture laisse la même entrée d'audit que l'écran.
