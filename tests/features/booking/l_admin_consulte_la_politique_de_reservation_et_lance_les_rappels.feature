Feature: L'admin consulte la politique de réservation et lance les rappels
  En tant qu'admin
  Je veux voir les constantes de réservation et lancer le job de rappel à la demande
  Afin que je sache quelles règles s'appliquent aux patients et que les rappels partent sans attendre le planning

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And a signed-in patient
    And a signed-in admin
    And the patient has a "BOOKED" appointment with "A" at "2026-11-20 12:00" in room "R1"
    And the patient has a "BOOKED" appointment with "A" at "2026-11-21 10:00" in room "R1"
    And the patient has a "BOOKED" appointment with "A" at "2026-11-21 10:30" in room "R1"

  Scenario: Un bouton lance le job de rappel : un rappel pour chaque RDV `BOOKED` qui commence dans les 24 heures et n'en a pas encore.
    When the admin runs the reminder job
    Then the admin is told 2 reminders were sent
    And the patient has "Rappel de RDV" notifications for the appointments at "2026-11-20 12:00, 2026-11-21 10:00"

  Scenario: Deux lancements successifs ne rappellent personne deux fois.
    When the admin runs the reminder job twice
    Then the admin is told 0 reminders were sent
    And the patient has "Rappel de RDV" notifications for the appointments at "2026-11-20 12:00, 2026-11-21 10:00"
    And 2 reminder emails were sent

  Scenario: Le job laisse une entrée d'audit avec le nombre de rappels quand il en crée.
    When the admin runs the reminder job twice
    Then the audit entry "booking.reminders_sent" has no actor and counts 2

  Scenario Outline: Règle §10 : seul l'admin lance les rappels à la demande (<case>)
    Given a signed-in "<role>" user
    When that user runs the reminder job
    Then the booking is refused as "forbidden"
    And no one was notified

    Examples:
      | case      | role      |
      | patient   | PATIENT   |
      | praticien | CLINICIAN |
