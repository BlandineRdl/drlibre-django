---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§10, §5.6, §5.8, §11, §14)
parent: aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md
depends_on: aidd_docs/backlog/stories/l-admin-liste-les-rdv-de-tous-les-hopitaux.md
---

# Story: L'admin annule ou change le statut de n'importe quel RDV
**As** admin
**I want** marquer arrivé, terminé, absent ou annuler n'importe quel RDV
**So that** je corrige l'activité de tout hôpital

## Acceptance
- Les transitions sont celles du personnel : `BOOKED` vers `CHECKED_IN`, `NO_SHOW` ou `CANCELLED` ; `CHECKED_IN` vers `COMPLETED` ou `CANCELLED` ; une autre renvoie `invalid_transition` avec le statut courant.
- Arrivée, terminé et absent ne notifient pas le patient.
- L'annulation exige un motif, ignore la règle des 24 heures, enregistre l'heure et le motif, notifie le patient (« RDV annulé ») et lui envoie un email, puis lance l'offre automatique de la liste d'attente.
- Les mêmes actions sont disponibles par `POST /appointments/{id}/check-in`, `/complete`, `/no-show` et `/cancel` (§14).
- Chaque action laisse une entrée d'audit sans motif ni donnée personnelle.
