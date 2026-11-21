Feature: Le patient voit son prochain rendez-vous dès l'accueil
  En tant que patient connecté, avec ou sans mot de passe
  Je veux voir en arrivant mon prochain RDV et mes notifications non lues
  Afin que je sache sans chercher ce qui m'attend

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And the agenda names the clinicians, the type and the rooms
    And a signed-in patient

  Scenario: L'accueil salue le patient, montre son prochain RDV à venir et le nombre de ses notifications non lues.
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-27 13:00" in room "R1"
    And the patient has a "BOOKED" appointment with "A" at "2026-11-25 13:00" in room "R1"
    And the patient has a "COMPLETED" appointment with "A" at "2026-11-18 13:00" in room "R1"
    And the patient has 2 unread notifications and 1 read one
    When the patient opens the home page
    Then the home page greets "Patient Test"
    And the home page shows only the appointment "mer. 25/11/2026 de 09:00 à 09:30, fuseau America/Martinique"
    And the home page says "2 notifications non lues."

  Scenario: L'accueil salue le patient, montre son prochain RDV à venir et le nombre de ses notifications non lues. (rien à venir)
    Given the patient has a "COMPLETED" appointment with "A" at "2026-11-18 13:00" in room "R1"
    When the patient opens the home page
    Then the home page greets "Patient Test"
    And the home page says "Aucun rendez-vous à venir."
    And the home page says "Aucune notification non lue."

  Scenario: Le nombre baisse quand le patient marque une notification comme lue.
    Given the patient has 2 unread notifications and 0 read one
    When the patient marks the first unread notification as read on the notifications page
    And the patient opens the home page
    Then the home page says "1 notification non lue."
    And the menu says "Notifications (1 non lue)"

  Scenario: L'action « Prendre un RDV » ouvre la recherche publique de l'Epic 3.
    When the patient opens the home page
    Then the action "Prendre un RDV" leads to the public search
