---
type: story
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§10, §3.1)
parent: aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md
depends_on:
  - aidd_docs/backlog/stories/l-admin-gere-les-specialites.md
  - aidd_docs/backlog/stories/l-admin-gere-les-salles-d-un-departement.md
  - aidd_docs/backlog/stories/l-admin-gere-les-comptes-utilisateurs.md
---

# Story: L'admin rattache un profil praticien
**As** admin
**I want** rattacher un profil à un utilisateur praticien actif qui n'en a pas
**So that** il soit placé dans un département, avec une spécialité et un poids round robin

## Acceptance
- Le profil porte un département, une spécialité, un titre, une bio, une salle par défaut (salle active de ce département) et un poids d'au moins 1, à 1 par défaut.
- Un département qui a des praticiens ne peut pas être supprimé ; une spécialité portée par un praticien non plus.
- Une salle qui est la salle par défaut d'un praticien ne peut ni être supprimée, ni changer de département tant que des praticiens de l'ancien département l'utilisent.
- Chaque écriture laisse une entrée d'audit sans donnée personnelle.
