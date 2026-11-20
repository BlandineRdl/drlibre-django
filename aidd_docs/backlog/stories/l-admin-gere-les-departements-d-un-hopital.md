---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§10, §3.2)
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
depends_on: aidd_docs/backlog/stories/l-admin-gere-les-hopitaux.md
---

# Story: L'admin gère les départements d'un hôpital
**As** admin
**I want** gérer les départements, chacun rattaché à un hôpital
**So that** l'organisation de chaque site soit représentée

## Acceptance
- Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation ; le code est unique.
- Un hôpital qui a des départements ne peut pas être supprimé, et le refus liste ses départements.
- Chaque écriture laisse une entrée d'audit sans donnée personnelle.
