Feature: L'email saisi rattache la réservation au bon patient
  En tant que patient
  Je veux que ma réservation sans connexion s'ajoute à mon compte existant
  Afin que tous mes RDV restent au même endroit, sans que mon compte soit révélé à d'autres

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And "A" and "B" are free at "2026-11-23 09:00"

  Scenario: Un email d'un patient actif, avec ou sans mot de passe, fait réserver pour ce patient ; les informations saisies ne changent pas son profil (avec mot de passe)
    Given an active patient with email "lea@example.org" and a password
    And the visitor types full_name "Un Autre Nom"
    And the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the appointment is "BOOKED" for "ONLINE"
    And the appointment belongs to the existing patient
    And the profile of the existing patient is unchanged

  Scenario: Un email d'un patient actif, avec ou sans mot de passe, fait réserver pour ce patient ; les informations saisies ne changent pas son profil (sans mot de passe)
    Given an active patient with email "lea@example.org" and no password
    And the visitor types full_name "Un Autre Nom"
    And the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the appointment belongs to the existing patient
    And the profile of the existing patient is unchanged

  Scenario Outline: Un email d'admin, de praticien ou d'utilisateur inactif fait refuser la réservation par un message générique qui n'en dit pas la raison (<case>)
    Given a user with role "<role>", <state>, and email "lea@example.org"
    And the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the booking is refused with a message that does not say why
    And the hold is released and nothing was created

    Examples:
      | case                      | state       | role      |
      | email d'admin             | active      | ADMIN     |
      | email de praticien        | active      | CLINICIAN |
      | email d'utilisateur inactif | inactive    | PATIENT   |

  Scenario: Aucune réponse ne révèle si un email a déjà un compte
    Given an active patient with email "lea@example.org" and a password
    When "lea@example.org" asks to hold "A" at "2026-11-23 09:00"
    And "inconnu@example.org" asks to hold "B" at "2026-11-23 09:00"
    Then both holds were answered and both codes emailed the same way

  Scenario: Avant la vérification du code, rien n'est renvoyé sur le patient ni sur ses autres RDV
    Given an active patient with email "lea@example.org" and a password
    And the patient has an active appointment with "B" from "2026-11-23 09:00" to "2026-11-23 09:30"
    When the visitor asks to hold "A" at "2026-11-23 09:00"
    Then the answer carries nothing about any patient or appointment
