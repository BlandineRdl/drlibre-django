---
type: epic
status: proposed
source: aidd_docs/memory/external/drlibre-specs.md (§9, §5.4, §5.6)
goal: aidd_docs/memory/project-brief.md
depends_on: aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md
---
# Epic: Le praticien pilote sa journée et ses rendez-vous
Un praticien voit son agenda du jour et de la semaine, fait avancer chaque RDV (arrivée, terminé, absent, annulé, déplacé) et tient ses notes cliniques, sans jamais voir les RDV d'un autre praticien.

## Context and Value
- Audience : praticien.
- Besoin : le praticien gère son activité au quotidien ; ses actions sur les statuts sont les seules qui ferment un RDV (§5.6).
- Valeur : des statuts à jour alimentent le reporting (no-shows, taux de réalisation) et les annulations libèrent des créneaux.

## Boundaries
- Includes:
  - Aujourd'hui : agenda d'un jour avec navigation précédent / suivant / aujourd'hui, indicateurs (RDV, annulés à part, terminés, absents, prochain créneau libre), RDV groupés par heure avec les actions autorisées (§9).
  - Calendrier : grille de la semaine de 07:00 à 19:00 par tranches de 30 min, RDV actifs dans la couleur de leur type, absences affichées (§9).
  - Fiche RDV : patient (nom, téléphone, âge), heure, type, salle, motif, statut ; arrivée, terminé, absent sans notification ; annulation avec motif et notification du patient ; déplacement depuis un bandeau de la semaine ; historique des entrées d'audit ; « Not your appointment » sur le RDV d'un autre praticien (§9, §5.6).
  - Notes cliniques de 5000 caractères au plus, enregistrées à part, visibles de ce seul praticien (§9, §3.1).
  - Personnel soumis seulement à la disponibilité et aux conflits, pas aux règles patient (§5.3).
  - Réservation par le praticien dans son propre agenda pour un patient actif (§5.4).
  - Patients : ceux qui ont au moins un RDV avec ce praticien, avec téléphone, dernière et prochaine visite, recherche par nom (§9).
  - Salles : frise du jour, de 07:00 à 19:00, des salles actives du département ; « Occupied » pour les RDV des autres praticiens (§9).
  - API des changements de statut, d'annulation et de déplacement (§14).
- Excludes:
  - Saisie des plages et des absences (Epic disponibilités).
  - Réservation, déplacement et annulation par l'admin sur tous les agendas (Epic supervision admin).
  - Statut `CONFIRMED` (supprimé, §17).

## Success Evidence
- Le praticien de démo passe un RDV de `BOOKED` à `CHECKED_IN` puis à `COMPLETED`, en marque un autre `NO_SHOW` et en annule un troisième ; le patient concerné reçoit une notification et un email.
- Une transition interdite renvoie `invalid_transition` avec le statut courant ; le RDV d'un autre praticien affiche « Not your appointment ».
- Les notes ne sont visibles que du praticien auteur et n'apparaissent dans aucune métadonnée d'audit.
- Scénarios BDD verts pour §5.6 (côté personnel) et les contrôles d'accès de §9 ; écrans conformes WCAG 2.2 AA, de 375 à 1440 px (§16).

## Dependencies and Unknowns
| Item | Kind | Handling |
| --- | --- | --- |
| Notifications, emails, annulation et déplacement | dependency | `depends_on` Epic 4 |
| Une annulation par le praticien lance l'offre de liste d'attente une fois l'Epic 5 livré | assumption | acceptée |
| §9 ne décrit aucun écran de réservation pour le praticien : réservation via l'API seulement (§14 `POST /appointments`) | assumption | acceptée |
