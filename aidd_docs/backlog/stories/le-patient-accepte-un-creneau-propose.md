---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.2, §5.3, §5.8 Accept, §8 Waitlist, §11, §7.6, §14)
parent: aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
depends_on: aidd_docs/backlog/stories/un-creneau-annule-est-propose-au-patient-en-attente-le-plus-ancien.md
---

# Story: Le patient accepte un créneau proposé
**As** patient connecté, avec ou sans mot de passe
**I want** accepter le créneau qu'on me propose
**So that** il devienne mon RDV

## Acceptance
- Accepter une de ses entrées `OFFERED` place un RDV avec le praticien, le type et le début offerts : RDV `BOOKED`, source `ONLINE` ; l'entrée passe en `BOOKED`.
- Les règles patient s'appliquent : début à au moins 120 min, moins de 3 réservations en ligne ouvertes, type réservable en ligne, créneau libre exact ; sinon `rule_violation` avec les règles violées.
- Si le créneau a été pris entre-temps, l'acceptation échoue en `conflict` avec les ressources en cause et l'entrée repasse en `WAITING`.
- La notification « Créneau réservé » ne porte que l'heure ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion.
- L'acceptation laisse une entrée d'audit sans donnée personnelle.
- `POST /waitlist/{id}/accept` applique les mêmes règles, sur les seules entrées du patient ; un praticien reçoit `forbidden`.
