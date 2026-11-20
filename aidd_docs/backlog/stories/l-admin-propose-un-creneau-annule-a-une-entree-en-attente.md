---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.8 Manual offer, §10 Waitlist, §11, §7.6)
parent: aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
depends_on:
  - aidd_docs/backlog/stories/l-admin-suit-la-liste-d-attente.md
  - aidd_docs/backlog/stories/un-creneau-annule-est-propose-au-patient-en-attente-le-plus-ancien.md
---

# Story: L'admin propose un créneau annulé à une entrée en attente
**As** admin
**I want** proposer à une entrée en attente le premier créneau annulé qui lui convient
**So that** un créneau libéré trouve preneur même sans offre automatique

## Acceptance
- Sur une entrée `WAITING`, l'offre manuelle retient le premier créneau annulé à venir du même type dans sa fenêtre, si son praticien est encore libre à cette heure et qu'aucune autre entrée ne détient cette offre.
- L'entrée passe en `OFFERED`, liée à ce RDV annulé, et le patient la voit avec l'heure proposée et le bouton « Accepter ».
- La notification « Créneau proposé » ne porte que l'heure ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion.
- L'offre laisse une entrée d'audit sans donnée personnelle.
