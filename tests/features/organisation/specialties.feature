Feature: L'admin gère les spécialités
  En tant qu'admin
  Je veux gérer une liste de spécialités (nom, code unique, actif)
  Afin que les praticiens soient classés sur des valeurs communes, cherchables et filtrables

  Scenario: Création d'une spécialité
    When the admin saves a specialty "CARDIO" named "Cardiologie"
    Then the specialty "CARDIO" is listed

  Scenario: Création : le code est unique, quelle que soit sa casse
    Given a specialty "CARDIO" exists
    When the admin saves a specialty "NEW" with code "cardio"
    Then the save is refused as invalid on "code"

  Scenario: Liste avec recherche et pagination par 20
    Given 21 specialty records exist, 2 of them named with "Pédiatrie"
    When the admin lists the specialty records on page 1
    Then the page shows 20 rows out of 21
    When the admin lists the specialty records searching "pédiatrie"
    Then the page shows 2 rows out of 2

  Scenario: Modification et suppression avec confirmation
    Given a specialty "CARDIO" exists
    And the admin is signed in on the console
    When the admin opens the deletion of the specialty "CARDIO"
    Then the deletion asks for confirmation and keeps the specialty "CARDIO"
    When the admin confirms the deletion
    Then no specialty "CARDIO" is stored

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle
    Given a specialty "CARDIO" exists
    When the admin deletes the specialty "CARDIO"
    Then the audit holds "specialty.deleted" for "CARDIO"
