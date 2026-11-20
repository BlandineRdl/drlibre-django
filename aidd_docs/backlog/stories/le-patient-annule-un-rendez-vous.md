---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.3, §5.6, §8 Cancel, §11, §7.6, §14, §4)
parent: aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md
depends_on:
  - aidd_docs/backlog/stories/le-patient-retrouve-ses-rendez-vous-a-venir-et-passes.md
  - aidd_docs/backlog/stories/le-patient-lit-ses-notifications-et-les-marque-comme-lues.md
---

# Story: Le patient annule un rendez-vous
**As** patient connecté, avec ou sans mot de passe
**I want** annuler un de mes RDV à venir en donnant un motif
**So that** le créneau soit libéré pour un autre patient

## Acceptance
- L'annulation passe par une boîte de confirmation avec un motif obligatoire ; sans motif, `invalid_input`.
- Un RDV qui commence dans moins de 24 h est refusé en `rule_violation` avec `cancellation_window_closed` ; l'action « Annuler » n'est proposée que quand les règles la permettent.
- Un RDV `COMPLETED`, `CANCELLED` ou `NO_SHOW` est refusé en `invalid_transition` avec son statut courant.
- Le RDV passe en `CANCELLED` avec la date et le motif de l'annulation, et rejoint les RDV passés.
- La notification « RDV annulé » est créée dans la même transaction ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion. Une annulation refusée ne notifie rien.
- L'annulation laisse une entrée d'audit sans le motif.
- `POST /appointments/{id}/cancel` applique les mêmes règles, sur les seuls RDV du patient.
