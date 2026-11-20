---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.1, §15.4, §15.5)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
depends_on:
  - aidd_docs/backlog/stories/un-client-sans-jeton-decouvre-le-referentiel-et-les-creneaux-libres.md
  - aidd_docs/backlog/stories/un-client-agit-avec-le-jeton-d-un-utilisateur-et-exactement-ses-droits.md
  - aidd_docs/backlog/stories/un-client-reserve-et-consulte-des-rdv-en-fhir.md
  - aidd_docs/backlog/stories/un-client-deplace-annule-et-change-le-statut-d-un-rdv-en-fhir.md
  - aidd_docs/backlog/stories/un-patient-rejoint-la-liste-d-attente-et-accepte-une-offre-en-fhir.md
  - aidd_docs/backlog/stories/un-client-lit-les-notifications-de-son-utilisateur-en-fhir.md
  - aidd_docs/backlog/stories/l-admin-consulte-le-journal-d-audit-en-fhir.md
  - aidd_docs/backlog/stories/l-admin-gere-le-referentiel-en-fhir.md
  - aidd_docs/backlog/stories/le-praticien-gere-ses-disponibilites-en-fhir.md
---

# Story: Un client découvre les capacités du serveur dans le CapabilityStatement
**As** client API
**I want** lire sans jeton ce que le serveur FHIR sert
**So that** je me configure sans lire la documentation du produit

## Acceptance
- `GET /fhir/metadata` renvoie sans jeton un `CapabilityStatement` FHIR 4.0.1 au format `application/fhir+json`.
- Il liste chaque ressource servie avec ses interactions, ses paramètres de recherche, ses `_include` et ses paramètres `_sort`.
- Il ne déclare rien que le serveur ne serve pas, et le serveur ne sert rien qu'il ne déclare pas.
