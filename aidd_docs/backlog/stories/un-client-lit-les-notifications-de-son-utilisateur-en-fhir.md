---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.2, §15.4, §15.5, §11)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
depends_on: aidd_docs/backlog/stories/un-client-agit-avec-le-jeton-d-un-utilisateur-et-exactement-ses-droits.md
---

# Story: Un client lit les notifications de son utilisateur en FHIR
**As** client API agissant pour un patient
**I want** lire les notifications du patient et les marquer comme lues
**So that** mon application le tienne informé comme le portail

## Acceptance
- Chaque notification est une `Communication` avec destinataire, catégorie (le type de notification), texte, `sent`, `received` (heure de lecture) et `about` le RDV.
- Seul le destinataire lit ses `Communication` ; celle d'un autre donne `forbidden`.
- Les recherches acceptent `recipient`, `category` et `sent`.
- Le destinataire peut renseigner `received` pour marquer une notification comme lue ; aucune création ni suppression n'est acceptée.
