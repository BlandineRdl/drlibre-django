---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§10, §12.2)
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
depends_on: aidd_docs/backlog/stories/chaque-role-n-accede-qu-a-son-espace.md
---

# Story: L'admin gère les comptes utilisateurs
**As** admin
**I want** créer des comptes avec un mot de passe temporaire et les modifier
**So that** le personnel et les patients créés par l'admin puissent se connecter

## Acceptance
- La liste se cherche par nom ou par email ; l'email est unique et enregistré en minuscules.
- Le nom, l'email, le rôle et l'état actif sont modifiables.
- Un admin ne peut ni désactiver son propre compte, ni changer son propre rôle.
- Désactiver un utilisateur coupe ses sessions immédiatement.
- Un praticien qui a des RDV actifs à venir ne peut pas être désactivé ; le refus liste ces RDV.
- La suppression est refusée pour son propre compte et pour un utilisateur qui est l'acteur d'entrées d'audit ; le message invite à désactiver le compte.
- Chaque écriture laisse une entrée d'audit sans donnée personnelle.
