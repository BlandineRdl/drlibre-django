---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.2, §5.3, §5.8 Accept, §11, §7.6, §14)
parent: aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
depends_on:
  - aidd_docs/backlog/stories/l-admin-suit-la-liste-d-attente.md
  - aidd_docs/backlog/stories/le-patient-accepte-un-creneau-propose.md
---

# Story: L'admin accepte une offre pour un patient
**As** admin
**I want** accepter l'offre d'une entrée pour son patient
**So that** le patient obtienne le RDV sans agir lui-même

## Acceptance
- L'admin accepte une entrée `OFFERED` de n'importe quel patient : RDV `BOOKED` placé avec le praticien, le type et le début offerts, source `STAFF` ; l'entrée passe en `BOOKED`.
- Seules les règles du personnel s'appliquent : créneau libre exact et absence de conflit.
- Si le créneau a été pris entre-temps, l'acceptation échoue en `conflict` avec les ressources en cause et l'entrée repasse en `WAITING`.
- La notification « Créneau réservé » ne porte que l'heure ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion.
- L'acceptation laisse une entrée d'audit dont l'acteur est l'admin, sans donnée personnelle.
- `POST /waitlist/{id}/accept` applique les mêmes règles pour l'admin.
