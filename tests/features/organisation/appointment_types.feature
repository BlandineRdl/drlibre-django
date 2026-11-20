Feature: L'admin gère les types de RDV d'un département
  En tant qu'admin
  Je veux gérer les types de RDV (durée, buffer, couleur, salle requise, réservable en ligne, actif)
  Afin que chaque département propose ses prestations

  Background:
    Given a hospital "NORD" exists
    And a department "CARD" exists in hospital "NORD"

  Scenario: La durée est d'au moins 1 minute et le buffer d'au moins 0 : un buffer nul est accepté
    When the admin saves an appointment type "CONSULT" with buffer_minutes "0"
    Then the appointment type "CONSULT" is listed

  Scenario Outline: La durée est d'au moins 1 minute et le buffer d'au moins 0 ; le code est unique (<field> <value>)
    Given an appointment type "TAKEN" exists in department "CARD"
    When the admin saves an appointment type "CONSULT" with <field> "<value>"
    Then the save is refused as invalid on "<field>"

    Examples:
      | field            | value   |
      | duration_minutes | 0       |
      | buffer_minutes   | -1      |
      | code             | taken   |
      | colour           | red     |
      | colour           | #12345G |
      | department_id    | nope    |

  Scenario: Création d'un type avec sa couleur
    When the admin saves an appointment type "CONSULT" with colour "#a1b2c3"
    Then the appointment type "CONSULT" has colour "#A1B2C3"

  Scenario: Liste avec recherche et pagination par 20
    Given 23 appointment type records exist, 2 of them named with "Écho"
    When the admin lists the appointment type records on page 2
    Then the page shows 3 rows out of 23
    When the admin lists the appointment type records searching "écho"
    Then the page shows 2 rows out of 2

  Scenario: Modification et suppression avec confirmation
    Given an appointment type "CONSULT" exists in department "CARD"
    And the admin is signed in on the console
    When the admin opens the deletion of the appointment type "CONSULT"
    Then the deletion asks for confirmation and keeps the appointment type "CONSULT"
    When the admin confirms the deletion
    Then no appointment type "CONSULT" is stored

  Scenario: Suppression : un type qui a des rendez-vous est refusé, avec ce qui l'utilise
    Given an appointment type "CONSULT" exists in department "CARD"
    And the appointment type "CONSULT" has an appointment
    When the admin deletes the appointment type "CONSULT"
    Then the delete is refused listing appointment "RDV 2026-12-01"

  Scenario: Un département qui a des types ne peut pas être supprimé, et le refus le dit
    Given an appointment type "CONSULT" exists in department "CARD"
    When the admin deletes the department "CARD"
    Then the delete is refused listing appointment_type "CONSULT"

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle
    When the admin saves an appointment type "CONSULT" named "Consultation"
    Then the audit holds "appointment_type.created" for "CONSULT"
