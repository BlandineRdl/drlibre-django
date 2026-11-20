---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§15.2, §15.4, §15.5, §3.1)
parent: aidd_docs/backlog/epics/un-client-fhir-r4-fait-tout-ce-que-les-ecrans-permettent-ni-plus-ni-moins.md
depends_on: aidd_docs/backlog/stories/un-client-agit-avec-le-jeton-d-un-utilisateur-et-exactement-ses-droits.md
---

# Story: L'admin consulte le journal d'audit en FHIR
**As** client API agissant pour un admin
**I want** rechercher les entrées du journal d'audit en `AuditEvent`
**So that** un outil externe exploite la traçabilité du produit

## Acceptance
- Chaque entrée d'audit est un `AuditEvent` avec action, heure, agent, entité, métadonnées en détails d'entité et correlation id ; les connexions y figurent.
- Seul l'admin lit et recherche les `AuditEvent` ; tout autre utilisateur reçoit `forbidden`.
- Les recherches acceptent `agent`, `entity`, `entity-type`, `action` et `date`.
- Aucune création, modification ni suppression d'`AuditEvent` n'est acceptée.
