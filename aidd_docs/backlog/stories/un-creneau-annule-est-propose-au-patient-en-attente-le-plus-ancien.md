---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.6 Cancel, §5.8 Automatic offer, §8 Waitlist, §11, §7.6)
parent: aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
depends_on: aidd_docs/backlog/stories/le-patient-s-inscrit-sur-la-liste-d-attente.md
---

# Story: Un créneau annulé est proposé au patient en attente le plus ancien
**As** patient inscrit sur la liste d'attente
**I want** qu'on me propose le créneau d'un RDV annulé qui me correspond
**So that** j'obtienne un RDV plus tôt

## Acceptance
- À l'annulation d'un RDV, les entrées candidates sont `WAITING`, du même type, sans praticien préféré ou avec le praticien libéré, et leur fenêtre contient le créneau libéré.
- La plus ancienne gagne (à égalité, le plus petit id) : elle passe en `OFFERED`, liée au RDV annulé. Une seule entrée reçoit l'offre ; sans candidate, rien ne change.
- L'entrée offerte montre au patient l'heure proposée et un bouton « Accepter ».
- L'offre ne réserve rien : le créneau reste libre pour toute autre réservation.
- La notification « Créneau proposé » ne porte que l'heure ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion.
- L'offre laisse une entrée d'audit sans donnée personnelle.
