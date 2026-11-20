---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§8 Profile, §10 Users) ; aidd_docs/backlog/epics-shadow-report.md
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
depends_on: aidd_docs/backlog/stories/le-personnel-se-connecte-par-mot-de-passe-et-arrive-dans-son-espace.md
---

# Story: Un utilisateur change son mot de passe
**As** utilisateur qui a un mot de passe (admin, praticien ou patient créé par un admin)
**I want** changer mon mot de passe
**So that** le mot de passe temporaire donné par l'admin ne reste pas en usage

## Acceptance
- Le changement exige le mot de passe actuel et un nouveau, différent, de 10 à 72 caractères.
- Après une connexion avec un mot de passe temporaire, l'utilisateur doit le changer avant d'accéder à son espace.
- Un patient sans mot de passe ne voit pas cette action.
- Le changement est audité, sans le mot de passe.
