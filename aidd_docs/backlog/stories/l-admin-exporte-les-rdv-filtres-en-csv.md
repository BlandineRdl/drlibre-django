---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10 Appointments, §13)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
depends_on: aidd_docs/backlog/stories/l-admin-liste-les-rdv-de-tous-les-hopitaux.md
---

# Story: L'admin exporte les RDV filtrés en CSV
**As** admin
**I want** exporter en CSV tout l'ensemble filtré, pas seulement la page affichée
**So that** j'analyse l'activité hors de l'application sans exposer de donnée personnelle

## Acceptance
- Colonnes : id du RDV, début, fin, statut, source, id patient, id praticien, id département, id type de RDV, id salle.
- Les instants sont en UTC au format ISO 8601.
- Aucun nom ni texte libre n'apparaît.
- Une cellule qui commence par `=`, `+`, `-` ou `@` est préfixée d'une apostrophe.
- L'export laisse une entrée d'audit avec le nombre de lignes.
