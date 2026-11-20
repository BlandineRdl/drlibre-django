---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §5.6, §5.3, §5.8, §11, §14)
parent: aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md
depends_on: aidd_docs/backlog/stories/le-praticien-consulte-la-fiche-d-un-rdv.md
---

# Story: Le praticien annule un RDV avec un motif
**As** praticien
**I want** annuler un de mes RDV en donnant un motif
**So that** le patient soit prévenu et le créneau libéré

## Acceptance
- L'annulation est possible depuis `BOOKED` ou `CHECKED_IN` ; depuis un autre statut, elle renvoie `invalid_transition` avec le statut courant.
- Le motif est obligatoire ; sans motif, `invalid_input`.
- La règle des 24 heures des patients ne s'applique pas au praticien.
- L'heure et le motif d'annulation sont enregistrés sur le RDV.
- Le patient reçoit une notification « RDV annulé », sans nom ni motif, et un email.
- L'annulation lance l'offre automatique de la liste d'attente sur le créneau libéré.
- Sur le RDV d'un autre praticien, l'annulation est refusée avec `forbidden`.
- L'annulation est aussi disponible par `POST /appointments/{id}/cancel` (§14).
- L'annulation laisse une entrée d'audit sans le motif ni donnée personnelle.
