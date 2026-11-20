---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§12.1)
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
depends_on: aidd_docs/backlog/stories/le-personnel-se-connecte-par-mot-de-passe-et-arrive-dans-son-espace.md
---

# Story: Un compte est verrouillé après des échecs répétés
**As** admin
**I want** que les tentatives répétées sur une adresse soient bloquées
**So that** les mots de passe ne puissent pas être devinés

## Acceptance
- Après 10 échecs en 15 minutes sur une adresse, la connexion de cette adresse est refusée jusqu'à la fin de la fenêtre.
- Une connexion réussie remet le compteur à zéro.
- Le verrouillage est audité avec seulement le domaine de l'email.
