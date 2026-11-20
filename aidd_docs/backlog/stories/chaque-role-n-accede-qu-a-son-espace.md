---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§12.3, §4)
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
depends_on: aidd_docs/backlog/stories/le-personnel-se-connecte-par-mot-de-passe-et-arrive-dans-son-espace.md
---

# Story: Chaque rôle n'accède qu'à son espace
**As** admin
**I want** que chaque page vérifie qui la demande
**So that** personne n'agisse hors de ses droits

## Acceptance
- Sans session, toute page non publique renvoie vers la connexion.
- Un utilisateur connecté qui ouvre l'espace d'un autre rôle voit une page « forbidden ».
- Un enregistrement absent donne `not_found` ; un enregistrement existant mais appartenant à un autre donne `forbidden`.
- Les requêtes d'écriture venant d'une autre origine sont refusées.
