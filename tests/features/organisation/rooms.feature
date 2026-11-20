Feature: L'admin gère les salles d'un département
  En tant qu'admin
  Je veux gérer les salles (code unique, étage, capacité d'au moins 1, équipements, actif)
  Afin que les RDV qui exigent une salle puissent en recevoir une

  Background:
    Given a hospital "NORD" exists
    And a department "CARD" exists in hospital "NORD"

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (création avec ses équipements)
    When the admin saves a room "R101" in department "CARD" with equipment "ECG,  tapis de marche ,,"
    Then the room "R101" has equipment "ECG|tapis de marche"

  Scenario Outline: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (création : capacité d'au moins 1, <case>)
    When the admin saves a room "R101" with capacity "<capacity>"
    Then the save is refused as invalid on "capacity"

    Examples:
      | case            | capacity |
      | zéro            | 0        |
      | négative        | -2       |
      | pas un nombre   | two      |

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (liste et recherche)
    Given 21 room records exist, 1 of them named with "Bloc"
    When the admin lists the room records on page 2
    Then the page shows 1 rows out of 21
    When the admin lists the room records searching "bloc"
    Then the page shows 1 rows out of 1

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (modification)
    Given a room "R101" exists in department "CARD"
    When the admin edits the room "R101" setting name "Salle d'effort"
    Then the room "R101" is named "Salle d'effort"
    And the audit holds "room.updated" for "R101" changing "name"

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation (suppression avec confirmation)
    Given a room "R101" exists in department "CARD"
    And the admin is signed in on the console
    When the admin opens the deletion of the room "R101"
    Then the deletion asks for confirmation and keeps the room "R101"
    When the admin confirms the deletion
    Then no room "R101" is stored

  Scenario: Règle §10 : une salle ne peut pas être supprimée tant qu'elle a des rendez-vous ou des règles de disponibilité
    Given a room "R101" exists in department "CARD"
    And the room "R101" is used by an availability rule and an appointment
    When the admin deletes the room "R101"
    Then the delete is refused listing availability_rule "Lundi 09:00" and appointment "RDV 2026-12-01"

  Scenario: Règle §4 : un enregistrement absent donne not_found
    When the admin deletes an unknown room
    Then the delete is refused as "not_found"

  Scenario: Un département qui a des salles ne peut pas être supprimé, et le refus le dit
    Given a room "R101" exists in department "CARD"
    When the admin deletes the department "CARD"
    Then the delete is refused listing room "R101"

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle
    When the admin saves a room "R101" in department "CARD" with equipment "ECG"
    Then the audit holds "room.created" for "R101"
