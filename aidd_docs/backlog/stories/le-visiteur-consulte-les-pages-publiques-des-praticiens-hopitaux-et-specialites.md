---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§6.6, §6.2, §4, §14)
parent: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
depends_on: aidd_docs/backlog/stories/chaque-resultat-montre-ses-prochaines-disponibilites.md
---

# Story: Le visiteur consulte les pages publiques des praticiens, hôpitaux et spécialités
**As** visiteur
**I want** ouvrir la page d'un praticien, d'un hôpital ou d'une spécialité
**So that** je voie tous les horaires et l'offre d'un lieu avant de choisir

## Acceptance
- Un résultat praticien mène à sa page par un lien vers tous ses horaires.
- La page praticien montre nom, titre, spécialité, bio, hôpital et département, ses types réservables en ligne, et un bandeau des créneaux libres du type choisi, du lundi au dimanche, avec semaine précédente et suivante.
- La page hôpital montre nom, adresse, téléphone, description, départements, spécialités et praticiens, chacun avec ses prochains créneaux libres.
- La page spécialité montre la liste des praticiens de cette spécialité.
- Ces pages s'ouvrent sans session et ne montrent aucune donnée non publique ; un enregistrement absent ou inactif donne `not_found`.
- `GET /providers/{id}`, `GET /hospitals/{id}`, `GET /specialties/{id}` et `GET /slots` répondent sans session.
