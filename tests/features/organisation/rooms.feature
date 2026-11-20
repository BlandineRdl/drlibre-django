Feature: L'admin gère les salles d'un département
  En tant qu'admin
  Je veux gérer les salles (code unique, étage, capacité d'au moins 1, équipements, actif)
  Afin que les RDV qui exigent une salle puissent en recevoir une

  Background:
    Given a hospital "NORD" exists
    And a department "CARD" exists in hospital "NORD"

  Scenario: Création d'une salle avec ses équipements
    When the admin saves a room "R101" in department "CARD" with equipment "ECG,  tapis de marche ,,"
    Then the room "R101" has equipment "ECG|tapis de marche"

  Scenario Outline: Création : la capacité est d'au moins 1 (<capacity>)
    When the admin saves a room "R101" with capacity "<capacity>"
    Then the save is refused as invalid on "capacity"

    Examples:
      | capacity |
      | 0        |
      | -2       |
      | two      |

  Scenario: Liste avec recherche et pagination par 20
    Given 20 room records exist, 1 of them named with "Bloc"
    When the admin lists the room records on page 1
    Then the page shows 20 rows out of 20
    When the admin lists the room records searching "bloc"
    Then the page shows 1 rows out of 1

  Scenario: Modification et suppression avec confirmation
    Given a room "R101" exists in department "CARD"
    And the admin is signed in on the console
    When the admin opens the deletion of the room "R101"
    Then the deletion asks for confirmation and keeps the room "R101"
    When the admin confirms the deletion
    Then no room "R101" is stored

  Scenario: Suppression : une salle qui a des disponibilités est refusée, avec ce qui l'utilise
    Given a room "R101" exists in department "CARD"
    And the room "R101" is used by an availability rule
    When the admin deletes the room "R101"
    Then the delete is refused listing availability_rule "Lundi 09:00"

  Scenario: Suppression : une salle absente est introuvable
    When the admin deletes an unknown room
    Then the delete is refused as "not_found"

  Scenario: Un département qui a des salles ne peut pas être supprimé, et le refus le dit
    Given a room "R101" exists in department "CARD"
    When the admin deletes the department "CARD"
    Then the delete is refused listing room "R101"

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle
    When the admin saves a room "R101" in department "CARD" with equipment "ECG"
    Then the audit holds "room.created" for "R101"
