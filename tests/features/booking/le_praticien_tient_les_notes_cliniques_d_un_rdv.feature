Feature: Le praticien tient les notes cliniques d'un RDV
  En tant que praticien
  Je veux écrire des notes cliniques sur un de mes RDV
  Afin que je garde la trace de la consultation

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And the signed-in clinician is "A"

  Scenario Outline: Les notes s'enregistrent depuis la fiche, à part des autres actions. (RDV <case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the clinician writes the notes "  Tension 12/8, revoir dans un mois  "
    Then the stored notes are "Tension 12/8, revoir dans un mois"
    And the appointment is now "<status>"
    And no one was notified

    Examples:
      | case    | status     |
      | réservé | BOOKED     |
      | arrivé  | CHECKED_IN |
      | terminé | COMPLETED  |
      | annulé  | CANCELLED  |
      | absent  | NO_SHOW    |

  Scenario: Les notes s'enregistrent depuis la fiche, à part des autres actions. (notes vidées)
    Given the patient has a "COMPLETED" appointment with "A" at "2026-11-20 08:00" in room "R1"
    And the appointment holds the notes "Tension 12/8"
    When the clinician writes the notes "   "
    Then the appointment has no notes

  Scenario: Au-delà de 5000 caractères, l'enregistrement est refusé avec `invalid_input`.
    Given the patient has a "COMPLETED" appointment with "A" at "2026-11-20 08:00" in room "R1"
    When the clinician writes notes of 5001 characters
    Then the booking is refused as "invalid_input"
    And the refusal names the field "clinical_notes"
    And nothing was changed or notified

  Scenario: Au-delà de 5000 caractères, l'enregistrement est refusé avec `invalid_input`. (5000 caractères acceptés)
    Given the patient has a "COMPLETED" appointment with "A" at "2026-11-20 08:00" in room "R1"
    When the clinician writes notes of 5000 characters
    Then the stored notes hold 5000 characters

  Scenario: Seul le praticien du RDV voit les notes : ni le patient, ni l'admin, ni un autre praticien. (autre praticien)
    Given the patient has a "COMPLETED" appointment with "A" at "2026-11-20 08:00" in room "R1"
    And the signed-in clinician is "B"
    When the clinician writes the notes "Tension 12/8"
    Then the booking is refused as "forbidden"
    And nothing was changed or notified

  Scenario: Seul le praticien du RDV voit les notes : ni le patient, ni l'admin, ni un autre praticien. (patient)
    Given the patient has a "COMPLETED" appointment with "A" at "2026-11-20 08:00" in room "R1"
    And the appointment holds the notes "Tension 12/8"
    Then the patient sees the appointment without its notes

  Scenario: L'enregistrement laisse une entrée d'audit qui nomme le champ modifié, jamais le texte des notes.
    Given the patient has a "COMPLETED" appointment with "A" at "2026-11-20 08:00" in room "R1"
    When the clinician writes the notes "Tension 12/8"
    Then the audit records the written field "clinical_notes" by the clinician, never the text
