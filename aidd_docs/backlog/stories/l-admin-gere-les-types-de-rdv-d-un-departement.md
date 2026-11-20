---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§10, §3.1)
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
depends_on: aidd_docs/backlog/stories/l-admin-gere-les-departements-d-un-hopital.md
---

# Story: L'admin gère les types de RDV d'un département
**As** admin
**I want** gérer les types de RDV (durée, buffer, couleur, salle requise, réservable en ligne, actif)
**So that** chaque département propose ses prestations

## Acceptance
- La durée est d'au moins 1 minute et le buffer d'au moins 0 ; le code est unique.
- Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation.
- Un département qui a des types ne peut pas être supprimé, et le refus le dit.
- Chaque écriture laisse une entrée d'audit sans donnée personnelle.
