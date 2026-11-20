---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.8 Join, §14, §4)
parent: aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
depends_on: aidd_docs/backlog/stories/l-admin-suit-la-liste-d-attente.md
---

# Story: L'admin inscrit un patient sur la liste d'attente
**As** admin
**I want** inscrire un patient sur la liste d'attente
**So that** un patient qui ne le fait pas lui-même puisse recevoir une offre

## Acceptance
- L'admin choisit un patient actif, un type actif, un praticien préféré actif facultatif et une fenêtre de dates ; l'entrée est créée en `WAITING` et apparaît dans la liste.
- Un patient, un type ou un praticien inconnu ou inactif donne `not_found`.
- L'inscription laisse une entrée d'audit sans donnée personnelle.
- `POST /waitlist` permet à l'admin de nommer le patient.
