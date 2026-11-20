---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.1, §15.2, §15.4, §15.5, §15.6, §5.1, §4)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
---

# Story: Un client sans jeton découvre le référentiel et les créneaux libres
**As** client API
**I want** lire sans jeton les hôpitaux, départements, salles, spécialités, types de RDV, praticiens et créneaux libres en FHIR R4
**So that** j'affiche l'offre de soins et ses disponibilités dans mon application

## Acceptance
- L'API sert FHIR R4 (4.0.1) en `application/fhir+json` sous `/fhir` ; chaque ressource garde l'id du produit comme id logique et porte `meta.versionId` et `meta.lastUpdated`.
- Sans jeton, lecture et recherche sont ouvertes sur les enregistrements actifs : `Organization` (hôpital de type `prov`, département de type `dept` `partOf` l'hôpital), `Location` (site avec adresse, téléphone, position et fuseau ; salle `partOf` le site), `HealthcareService`, `CodeSystem` et `ValueSet` des spécialités, `Practitioner` et `PractitionerRole` limités aux champs publics, `Schedule`.
- Un enregistrement inactif ou absent donne `not_found` ; l'email et le téléphone d'un praticien ne sont pas renvoyés.
- Les recherches acceptent les paramètres du §15.5 pour ces ressources et `_include` `PractitionerRole:practitioner`, `PractitionerRole:organization`, `Slot:schedule`.
- Une recherche renvoie un Bundle `searchset` avec `total` et les liens `self`, `next` et `previous` ; `_count` fixe la taille de page, 20 par défaut, 100 au plus ; `_sort` est accepté sur les paramètres listés.
- Une recherche `Slot` exige `service-type` et une plage `start` de 31 jours au plus, sinon `invalid_input` ; elle renvoie seulement les créneaux libres de §5.1, avec un id stable pour un même schedule, type et début.
- Sans jeton, toute écriture renvoie `unauthenticated` (401).
- Chaque erreur est un `OperationOutcome` avec le statut HTTP du §4.
