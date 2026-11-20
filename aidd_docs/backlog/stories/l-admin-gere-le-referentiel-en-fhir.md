---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.2, §15.4, §10, §3.1)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
depends_on: aidd_docs/backlog/stories/un-client-agit-avec-le-jeton-d-un-utilisateur-et-exactement-ses-droits.md
---

# Story: L'admin gère le référentiel en FHIR
**As** client API agissant pour un admin
**I want** créer, modifier et supprimer hôpitaux, départements, salles, spécialités, types de RDV, utilisateurs et profils praticiens en FHIR
**So that** un outil externe maintienne l'organisation sans passer par la console

## Acceptance
- L'admin seul crée, modifie et supprime `Organization`, `Location`, `HealthcareService`, `CodeSystem`, `ValueSet`, `Practitioner` et `PractitionerRole` ; tout autre utilisateur reçoit `forbidden`.
- L'admin crée, modifie et supprime aussi `Patient`.
- Les extensions portent ce que FHIR n'a pas : étage, capacité et équipements de la salle ; durée, battement, couleur, salle exigée et réservable en ligne du type ; poids round robin du profil.
- Les règles sont celles de la console : codes uniques, refus `has_dependents` avec ce qui dépend encore de l'enregistrement, salle qui ne change pas de département tant que des praticiens de l'ancien l'ont par défaut, admin qui ne désactive pas son propre compte ni ne change son propre rôle.
- Une mise à jour avec un `If-Match` périmé échoue en 412.
- Chaque écriture laisse la même entrée d'audit que la console.
