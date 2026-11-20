---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§10, §3.1)
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
depends_on: aidd_docs/backlog/stories/l-admin-gere-les-departements-d-un-hopital.md
---

# Story: L'admin gère les salles d'un département
**As** admin
**I want** gérer les salles (code unique, étage, capacité d'au moins 1, équipements, actif)
**So that** les RDV qui exigent une salle puissent en recevoir une

## Acceptance
- Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation.
- Un département qui a des salles ne peut pas être supprimé, et le refus le dit.
- Chaque écriture laisse une entrée d'audit sans donnée personnelle.
