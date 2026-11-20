---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.8 Join, §8 Waitlist, §14, §4, §17)
parent: aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
---

# Story: Le patient s'inscrit sur la liste d'attente
**As** patient connecté, avec ou sans mot de passe
**I want** m'inscrire en attente d'un créneau pour un type de RDV
**So that** un créneau libéré puisse m'être proposé

## Acceptance
- Le formulaire demande un type de RDV, un praticien préféré facultatif et une fenêtre de dates ; l'entrée est créée en `WAITING` pour le patient de la session, qui ne peut nommer personne d'autre.
- Un type ou un praticien préféré inconnu ou inactif donne `not_found`.
- Le patient voit la liste de ses entrées avec leur statut.
- L'inscription laisse une entrée d'audit sans donnée personnelle.
- `POST /waitlist` applique les mêmes règles ; sans session, `unauthenticated` ; un praticien reçoit `forbidden`.
