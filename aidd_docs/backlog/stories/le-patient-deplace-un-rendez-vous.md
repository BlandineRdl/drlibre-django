---
type: story
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§5.2, §5.3, §5.6, §8 Reschedule, §11, §7.6, §14, §4)
parent: aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md
depends_on:
  - aidd_docs/backlog/stories/le-patient-retrouve-ses-rendez-vous-a-venir-et-passes.md
  - aidd_docs/backlog/stories/le-patient-lit-ses-notifications-et-les-marque-comme-lues.md
---

# Story: Le patient déplace un rendez-vous
**As** patient connecté, avec ou sans mot de passe
**I want** déplacer un RDV vers un autre créneau du même praticien
**So that** je garde mon RDV quand l'heure ne me convient plus

## Acceptance
- Seul un RDV `BOOKED` se déplace ; l'action « Déplacer » n'est proposée que quand les règles la permettent.
- Un bandeau à la semaine propose les créneaux libres du même praticien pour le même type ; la fin est recalculée, jamais reçue de l'appelant.
- Refus en `rule_violation` avec les règles violées : RDV actuel à moins de 24 h (`cancellation_window_closed`), nouveau début à moins de 120 min (`lead_time_too_short`), type non réservable en ligne (`type_not_bookable_online`), début hors des créneaux libres (`outside_availability`).
- Un chevauchement avec un autre RDV du patient, du praticien ou de la salle donne `conflict` avec les ressources en cause ; le RDV déplacé est ignoré.
- La salle actuelle est gardée si elle est libre, sinon la salle par défaut du praticien, sinon la première salle libre du département ; aucune salle libre donne `no_room_available`.
- La notification « RDV déplacé » porte la nouvelle heure et est créée dans la même transaction ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion. Un déplacement refusé ne notifie rien.
- Le déplacement laisse une entrée d'audit sans donnée personnelle.
- `POST /appointments/{id}/reschedule` applique les mêmes règles, sur les seuls RDV du patient.
