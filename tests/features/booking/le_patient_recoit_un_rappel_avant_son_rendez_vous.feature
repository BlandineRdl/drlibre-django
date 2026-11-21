Feature: Le patient reçoit un rappel avant son rendez-vous
  En tant que patient avec un RDV réservé
  Je veux être rappelé dans les 24 h qui précèdent mon RDV
  Afin que je ne le manque pas

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And a signed-in patient
    And the patient has a "BOOKED" appointment with "A" at "2026-11-20 12:00" in room "R1"
    And the patient has a "BOOKED" appointment with "A" at "2026-11-21 10:00" in room "R1"
    And the patient has a "BOOKED" appointment with "A" at "2026-11-21 10:30" in room "R1"

  Scenario: Exécuté sur planning, sans action d'un admin, le job de rappel crée une notification « Rappel de RDV » pour chaque RDV `BOOKED` qui commence dans les 24 prochaines heures et n'a pas encore de rappel. (premier passage)
    When the reminder job runs
    Then the patient has "Rappel de RDV" notifications for the appointments at "2026-11-20 12:00, 2026-11-21 10:00"

  Scenario: Exécuté sur planning, sans action d'un admin, le job de rappel crée une notification « Rappel de RDV » pour chaque RDV `BOOKED` qui commence dans les 24 prochaines heures et n'a pas encore de rappel. (rappel déjà envoyé)
    Given the reminder job ran
    And 30 minutes pass
    When the reminder job runs
    Then the patient has "Rappel de RDV" notifications for the appointments at "2026-11-20 12:00, 2026-11-21 10:00, 2026-11-21 10:30"

  Scenario: Deux exécutions ne créent qu'un rappel par RDV ; un RDV d'un autre statut n'en reçoit aucun. (deux exécutions)
    When the reminder job runs twice
    Then the patient has "Rappel de RDV" notifications for the appointments at "2026-11-20 12:00, 2026-11-21 10:00"
    And 2 reminder emails were sent

  Scenario Outline: Deux exécutions ne créent qu'un rappel par RDV ; un RDV d'un autre statut n'en reçoit aucun. (<case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-20 15:00" in room "R1"
    When the reminder job runs
    Then the patient has "Rappel de RDV" notifications for the appointments at "2026-11-20 12:00, 2026-11-21 10:00"

    Examples:
      | case    | status     |
      | arrivé  | CHECKED_IN |
      | terminé | COMPLETED  |
      | annulé  | CANCELLED  |
      | absent  | NO_SHOW    |

  Scenario: Chaque rappel envoie un email après la validation de la transaction, avec l'heure, l'hôpital et le praticien, sans motif, qui ne renvoie qu'à la page de connexion.
    When the reminder job runs
    Then each reminder email names the time, hospital and provider, without the reason, linking only to the sign-in page

  Scenario: Une exécution qui crée des rappels laisse une entrée d'audit avec leur nombre ; une exécution qui n'en crée aucun n'en laisse pas.
    When the reminder job runs twice
    Then the audit holds 1 "booking.reminders_sent" entries
    And the audit entry "booking.reminders_sent" has no actor and counts 2
