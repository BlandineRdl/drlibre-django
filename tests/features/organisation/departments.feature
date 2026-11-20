Feature: L'admin gère les départements d'un hôpital
  En tant qu'admin
  Je veux gérer les départements, chacun rattaché à un hôpital
  Afin que l'organisation de chaque site soit représentée

  Background:
    Given a hospital "NORD" exists

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation ; le code est unique (création dans son hôpital)
    When the admin saves a department "CARD" in hospital "NORD"
    Then the department "CARD" is listed

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation ; le code est unique (code déjà pris)
    Given a department "CARD" exists in hospital "NORD"
    When the admin saves a department "NEW" with code "CARD"
    Then the save is refused as invalid on "code"

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation ; le code est unique (liste et recherche)
    Given 22 department records exist, 4 of them named with "Radiologie"
    When the admin lists the department records on page 2
    Then the page shows 2 rows out of 22
    When the admin lists the department records searching "radio"
    Then the page shows 4 rows out of 4

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation ; le code est unique (modification)
    Given a department "CARD" exists in hospital "NORD"
    When the admin edits the department "CARD" setting name "Cardiologie adulte"
    Then the department "CARD" is named "Cardiologie adulte"
    And the audit holds "department.updated" for "CARD" changing "name"

  Scenario: Création, liste avec recherche et pagination par 20, modification et suppression avec confirmation ; le code est unique (suppression avec confirmation)
    Given a department "CARD" exists in hospital "NORD"
    And the admin is signed in on the console
    When the admin opens the deletion of the department "CARD"
    Then the deletion asks for confirmation and keeps the department "CARD"
    When the admin confirms the deletion
    Then no department "CARD" is stored

  Scenario: Règle §3.2 : un département appartient à un hôpital existant
    When the admin saves a department "CARD" with hospital_id "00000000-0000-4000-8000-000000000000"
    Then the save is refused as invalid on "hospital_id"

  Scenario: Un hôpital qui a des départements ne peut pas être supprimé, et le refus liste ses départements
    Given a department "CARD" exists in hospital "NORD"
    When the admin deletes the hospital "NORD"
    Then the delete is refused listing department "CARD"
    And nothing is audited

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle
    When the admin saves a department "CARD" in hospital "NORD"
    Then the audit holds "department.created" for "CARD"
