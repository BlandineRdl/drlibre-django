---
type: epic
status: ready
source: aidd_docs/memory/external/drlibre-specs.md (§5.6, §5.7, §7.4, §7.6, §8, §11)
goal: aidd_docs/memory/project-brief.md
depends_on: aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md
---
# Epic: Le patient gère ses rendez-vous et reste informé
Un patient connecté, avec ou sans mot de passe, retrouve tous ses RDV, les déplace ou les annule dans les règles, et est prévenu dans l'application et par email de chaque changement et de chaque rappel.

## Context and Value
- Audience : patient, en particulier le patient sans mot de passe, qui n'est souvent pas connecté quand un événement survient (§7.6).
- Besoin : après sa réservation, le patient doit garder la main sur ses RDV. L'application actuelle ne notifie que dans l'application (17.6), et le rappel ne part que si un admin le déclenche (§17).
- Valeur : moins de RDV manqués, des créneaux libérés tôt grâce à la règle des 24 h.

## Boundaries
- Includes:
  - Accueil du portail : prochain RDV, nombre de notifications non lues, action « Prendre un RDV » qui renvoie vers la recherche (§8).
  - RDV à venir (`BOOKED` ou `CHECKED_IN`, pas encore commencés) et passés, avec qui, quand (fuseau nommé), où (hôpital, adresse, département, salle), type, statut et motif (§7.4, §8).
  - Déplacement d'un RDV `BOOKED` (même praticien et même type, bandeau de créneaux à la semaine) et annulation avec motif obligatoire, règles de 120 min et de 24 h, salle réattribuée en privilégiant l'actuelle (§5.3, §5.6, §8).
  - Fichier `.ics` pour chaque RDV (§8).
  - Notifications in-app : RDV réservé, déplacé, annulé, rappel ; créées dans la même transaction que l'événement ; heure seulement, sans nom, motif ni email ; liste avec « marquer comme lu » (§11, §8).
  - Email pour chaque notification patient, sans lien qui connecte (§7.6).
  - Job de rappel idempotent pour les RDV `BOOKED` des 24 prochaines heures, exécuté sur planning, avec une entrée d'audit portant le nombre de rappels (§5.7, §17).
  - Profil : téléphone et date de naissance modifiables ; changement de mot de passe, masqué pour les patients sans mot de passe (§8).
- Excludes:
  - Liste d'attente : inscription, offres, acceptation, notifications et emails associés (Epic liste d'attente).
  - Déclenchement manuel du job de rappel depuis les réglages (Epic supervision admin).
  - Actions du personnel sur les statuts, déplacements et annulations côté staff (Epics espace praticien et supervision admin) ; elles réutilisent les notifications livrées ici.
  - Statut `CONFIRMED` et toute confirmation de venue par le patient (supprimés, §17).
  - Définir un mot de passe pour un patient sans mot de passe, SMS (hors périmètre).

## Success Evidence
- Le patient de démo, connecté par lien, voit son RDV, le déplace puis l'annule ; chaque étape crée une notification in-app et un email visible dans Mailpit, sans motif ni nom.
- Un déplacement ou une annulation à moins de 24 h est refusé avec `cancellation_window_closed`.
- Deux exécutions du job de rappel ne créent qu'un rappel par RDV ; le planning l'exécute sans action d'un admin.
- Scénarios BDD verts pour §5.6 (côté patient), §5.7 et §11 ; écrans conformes WCAG 2.2 AA, de 375 à 1440 px (§16).

## Dependencies and Unknowns
| Item | Kind | Handling |
| --- | --- | --- |
| Réservation, session patient, envoi d'emails | dependency | `depends_on` Epic 3 |
| Statut `CONFIRMED` retiré des statuts et des transitions (§5.6, §17) | decision | prise : supprimé |
| Notification in-app « RDV réservé » ajoutée au placement livré par l'Epic 3 | assumption | acceptée |
