---
type: epic
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§5.8, §8 Waitlist, §10 Waitlist, §11)
goal: aidd_docs/memory/project-brief.md
depends_on: aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md
---
# Epic: Les créneaux libérés sont proposés aux patients en liste d'attente
Quand un RDV est annulé, son créneau est proposé au patient en attente le plus ancien qui correspond, qui peut l'accepter et obtenir un RDV.

## Context and Value
- Audience : patient connecté, avec ou sans mot de passe (17.12) ; admin qui gère la file.
- Besoin : l'application actuelle définit l'expiration des entrées mais ne l'exécute jamais (§17).
- Valeur : un créneau annulé retrouve vite un patient au lieu de rester vide.

## Boundaries
- Includes:
  - Inscription par le patient pour lui-même : type actif, praticien préféré actif en option, fenêtre de dates ; liste de ses entrées avec leur statut (§5.8, §8).
  - Offre automatique à l'annulation : entrée `WAITING` la plus ancienne avec le même type, un praticien compatible et une fenêtre qui contient le créneau ; elle passe en `OFFERED` (§5.8).
  - Acceptation par le patient ou par un admin : placement complet (§5.2), donc conflits et règles appliqués ; l'entrée passe en `BOOKED` ; une offre ne réserve rien, et l'acceptation échoue en `conflict` si le créneau est pris (§5.8).
  - Expiration planifiée des entrées `WAITING` dont la date limite est passée (§5.8, §17).
  - Notifications in-app et emails « créneau proposé » et « créneau réservé » (§11, §7.6).
  - Côté admin : liste filtrée par statut (les plus anciennes d'abord), ajout d'un patient, offre manuelle du premier créneau annulé à venir dans la fenêtre (§10, §5.8).
  - API `POST /waitlist` et `POST /waitlist/{id}/accept` (§14).
- Excludes:
  - Inscription par un praticien (interdite, §5.8).
  - Liste d'attente pour un visiteur non connecté (17.12).

## Success Evidence
- Sur la seed : un patient s'inscrit, un autre annule un RDV correspondant, le premier reçoit l'offre (in-app et Mailpit), l'accepte et obtient un RDV `BOOKED`.
- Si le créneau est pris avant l'acceptation, celle-ci échoue en `conflict`.
- Une entrée dont la fenêtre est passée devient `EXPIRED` sans action d'un admin.
- Scénarios BDD verts pour chaque règle de §5.8 ; écrans conformes WCAG 2.2 AA, de 375 à 1440 px (§16).

## Dependencies and Unknowns
| Item | Kind | Handling |
| --- | --- | --- |
| Annulation, notifications et emails patient | dependency | `depends_on` Epic 4 |
| Source du RDV créé par acceptation : `ONLINE` si le patient accepte, `STAFF` si c'est un admin (non spécifié) | assumption | acceptée |
| Après un échec en `conflict`, l'entrée repasse en `WAITING` (non spécifié) | assumption | acceptée |
