---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.8) ; aidd_docs/backlog/epics-shadow-report.md
parent: aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
depends_on:
  - aidd_docs/backlog/stories/un-creneau-annule-est-propose-au-patient-en-attente-le-plus-ancien.md
  - aidd_docs/backlog/stories/une-entree-dont-la-fenetre-est-passee-expire.md
---

# Story: Une offre non acceptée à temps libère l'entrée
**As** patient inscrit sur la liste d'attente
**I want** que mon entrée revienne en attente si je n'ai pas accepté le créneau avant qu'il commence
**So that** un autre créneau puisse m'être proposé

## Acceptance
- Quand le créneau d'une entrée `OFFERED` commence sans acceptation, le job d'expiration la fait repasser en `WAITING`, ou en `EXPIRED` si sa date limite est passée.
- Revenue en `WAITING`, l'entrée peut recevoir une nouvelle offre.
- Le changement laisse une entrée d'audit sans donnée personnelle.
