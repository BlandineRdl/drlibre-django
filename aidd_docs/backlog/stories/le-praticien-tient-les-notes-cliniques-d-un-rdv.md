---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §3.1, §4)
parent: aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md
depends_on: aidd_docs/backlog/stories/le-praticien-consulte-la-fiche-d-un-rdv.md
---

# Story: Le praticien tient les notes cliniques d'un RDV
**As** praticien
**I want** écrire des notes cliniques sur un de mes RDV
**So that** je garde la trace de la consultation

## Acceptance
- Les notes s'enregistrent depuis la fiche, à part des autres actions.
- Au-delà de 5000 caractères, l'enregistrement est refusé avec `invalid_input`.
- Seul le praticien du RDV voit les notes : ni le patient, ni l'admin, ni un autre praticien.
- L'enregistrement laisse une entrée d'audit qui nomme le champ modifié, jamais le texte des notes.
