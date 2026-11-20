---
type: epic
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§10 Dashboard, Appointments, Audit log, Settings ; §13)
goal: aidd_docs/memory/project-brief.md
depends_on:
  - aidd_docs/backlog/epics/le-praticien-pilote-sa-journee-et-ses-rendez-vous.md
  - aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md
---
# Epic: L'admin supervise l'activité de tous les hôpitaux
Un admin global suit l'activité sur un tableau de bord chiffré, intervient sur n'importe quel RDV, exporte les données sans donnée personnelle et consulte le journal d'audit.

## Context and Value
- Audience : admin global (17.2).
- Besoin : une équipe pilote tous les hôpitaux ; elle doit mesurer l'utilisation et intervenir pour les patients (§1, §10).
- Valeur : visibilité sur l'utilisation, les absences et la part de réservation en ligne ; traçabilité de chaque écriture.

## Boundaries
- Includes:
  - Tableau de bord : période d'aujourd'hui, de 7 jours (par défaut) ou de 30 jours finissant aujourd'hui ; indicateurs de §13 (RDV, annulations, utilisation, taux d'absence, part en ligne, taille de la liste d'attente) ; « n/a » quand le dénominateur est nul ; histogramme des RDV par jour ; 5 praticiens les plus chargés (§10, §13).
  - RDV : liste filtrée par période, département, praticien, statut et source, les plus récents d'abord, 20 par page (§10, §4).
  - Export CSV de tout l'ensemble filtré : identifiants seulement, instants en UTC ISO 8601, protection contre l'injection de formules, export audité avec le nombre de lignes (§13).
  - Réservation pour un patient choisi par nom ou email : assistant sans « premier disponible », types non réservables en ligne inclus, praticien toujours nommé, salle choisie possible, source `STAFF` (§10, §5.2, §5.4).
  - Déplacement, annulation et changements de statut sur n'importe quel RDV, avec les règles du personnel (§10, §5.6).
  - Journal d'audit en lecture seule : les plus récents d'abord, filtres par acteur, type d'entité et période ; heure, acteur, action, entité, correlation id (§10).
  - Réglages : constantes de la politique de réservation en lecture seule, bouton qui lance le job de rappel (§10, §5.7, §14 `POST /jobs/reminders`).
- Excludes:
  - Gestion du référentiel et des utilisateurs (Epic 1).
  - Liste d'attente côté admin (Epic liste d'attente).
  - Constantes de la politique de réservation modifiables, admins par hôpital (non spécifié, §17).

## Success Evidence
- Sur la seed (RDV dans tous les statuts), chaque indicateur du tableau de bord est égal à sa définition de §13 recalculée en test ; un dénominateur nul affiche « n/a ».
- Le CSV exporté ne contient ni nom ni texte libre, et une cellule qui commence par `=` est préfixée d'une apostrophe.
- L'admin réserve pour un patient un type non réservable en ligne : le RDV est créé en source `STAFF`.
- Scénarios BDD verts pour §13 et pour les actions admin de §10 ; écrans conformes WCAG 2.2 AA, de 375 à 1440 px (§16).

## Dependencies and Unknowns
| Item | Kind | Handling |
| --- | --- | --- |
| Règles du personnel sur les statuts, l'annulation et le déplacement | dependency | `depends_on` Epic 6 |
| Entrées de la liste d'attente pour l'indicateur « taille » | dependency | `depends_on` Epic 5 |
| « Praticiens les plus chargés » classés par nombre de RDV non annulés sur la période (non spécifié) | assumption | acceptée |
| Les jours de la période sont comptés dans le fuseau de l'hôpital de chaque RDV (multi-fuseaux non spécifié) | assumption | acceptée |
