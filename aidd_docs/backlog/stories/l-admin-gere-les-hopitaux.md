---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§10, §3.1)
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
depends_on: aidd_docs/backlog/stories/chaque-role-n-accede-qu-a-son-espace.md
---

# Story: L'admin gère les hôpitaux
**As** admin
**I want** créer, consulter, modifier, supprimer et rechercher des hôpitaux
**So that** chaque site existe avec son adresse et son fuseau horaire

## Acceptance
- Un hôpital porte les champs du §3.1 (nom, code unique, description, adresse, code postal, ville, pays, téléphone, fuseau horaire, latitude et longitude optionnelles, actif).
- La liste montre 20 lignes par page, avec le total et une recherche.
- La suppression demande une confirmation.
- Chaque écriture laisse une entrée d'audit sans donnée personnelle.
