---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.8 Expiry, §17, §4)
parent: aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
depends_on: aidd_docs/backlog/stories/le-patient-s-inscrit-sur-la-liste-d-attente.md
---

# Story: Une entrée dont la fenêtre est passée expire
**As** patient inscrit sur la liste d'attente
**I want** que mon entrée expire quand sa fenêtre est passée
**So that** la liste ne garde que des attentes encore utiles

## Acceptance
- Exécuté sur planning, sans action d'un admin, le job d'expiration fait passer en `EXPIRED` chaque entrée `WAITING` dont la date limite est passée.
- Une entrée `EXPIRED` ne reçoit plus d'offre.
- L'expiration laisse une entrée d'audit sans donnée personnelle.
