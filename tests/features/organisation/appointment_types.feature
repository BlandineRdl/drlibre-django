Feature: L'admin gère les types de RDV d'un département
  En tant qu'admin
  Je veux gérer les types de RDV (durée, buffer, couleur, salle requise, réservable en ligne, actif)
  Afin que chaque département propose ses prestations

  Background:
    Given a hospital "NORD" exists
    And a department "CARD" exists in hospital "NORD"

  Scenario: La durée est d'au moins 1 minute et le buffer d'au moins 0 ; le code est unique (buffer nul accepté)
    When the admin saves an appointment type "CONSULT" with buffer_minutes "0"
    Then the appointment type "CONSULT" is listed

  Scenario Outline: La durée est d'au moins 1 minute et le buffer d'au moins 0 ; le code est unique (<case>)
    Given an appointment type "TAKEN" exists in department "CARD"
    When the admin saves an appointment type "CONSULT" with <field> "<value>"
    Then the save is refused as invalid on "<field>"

    Examples:
      | case           | field            | value |
      | durée nulle    | duration_minutes | 0     |
      | buffer négatif | buffer_minutes   | -1    |
      | code déjà pris | code             | taken |

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (création avec sa couleur)
    When the admin saves an appointment type "CONSULT" with colour "#a1b2c3"
    Then the appointment type "CONSULT" has colour "#A1B2C3"

  Scenario Outline: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (création refusée : <case>)
    When the admin saves an appointment type "CONSULT" with <field> "<value>"
    Then the save is refused as invalid on "<field>"

    Examples:
      | case                     | field         | value   |
      | couleur en toutes lettres | colour        | red     |
      | couleur mal formée       | colour        | #12345G |
      | département inconnu      | department_id | nope    |

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (liste et recherche)
    Given 23 appointment type records exist, 2 of them named with "Écho"
    When the admin lists the appointment type records on page 2
    Then the page shows 3 rows out of 23
    When the admin lists the appointment type records searching "écho"
    Then the page shows 2 rows out of 2

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (modification)
    Given an appointment type "CONSULT" exists in department "CARD"
    When the admin edits the appointment type "CONSULT" setting name "Première consultation"
    Then the appointment type "CONSULT" is named "Première consultation"
    And the audit holds "appointment_type.updated" for "CONSULT" changing "name"

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (suppression avec confirmation)
    Given an appointment type "CONSULT" exists in department "CARD"
    And the admin is signed in on the console
    When the admin opens the deletion of the appointment type "CONSULT"
    Then the deletion asks for confirmation and keeps the appointment type "CONSULT"
    When the admin confirms the deletion
    Then no appointment type "CONSULT" is stored

  Scenario: Règle §10 : un type de RDV ne peut pas être supprimé tant qu'il a des rendez-vous ou des inscriptions en liste d'attente
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
