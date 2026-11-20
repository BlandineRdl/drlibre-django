Feature: L'admin gère les hôpitaux
  En tant qu'admin
  Je veux créer, consulter, modifier, supprimer et rechercher des hôpitaux
  Afin que chaque site existe avec son adresse et son fuseau horaire

  Scenario: Un hôpital porte les champs du §3.1, dont son fuseau horaire
    When the admin saves a hospital "NORD" named "Hôpital Nord"
    Then the hospital "NORD" is listed with time zone "Europe/Paris"

  Scenario Outline: Un hôpital porte les champs du §3.1 (valeur refusée : <case>)
    Given a hospital "TAKEN" exists
    When the admin saves a hospital "NEW" with <field> "<value>"
    Then the save is refused as invalid on "<field>"
    And nothing is audited

    Examples:
      | case                    | field     | value        |
      | code déjà pris          | code      | taken        |
      | code avec des espaces   | code      | no spaces!   |
      | fuseau horaire inconnu  | time_zone | Mars/Olympus |
      | latitude hors limites   | latitude  | 95           |
      | longitude non numérique | longitude | east         |
      | nom vide                | name      |              |

  Scenario: Règle §4 : un enregistrement absent donne not_found
    When the admin edits an unknown hospital
    Then the save is refused as "not_found"

  Scenario: La liste montre 20 lignes par page, avec le total et une recherche (pagination)
    Given 25 hospital records exist, 3 of them named with "Nord"
    When the admin lists the hospital records on page 2
    Then the page shows 5 rows out of 25

  Scenario: La liste montre 20 lignes par page, avec le total et une recherche (recherche par nom ou code)
    Given 25 hospital records exist, 3 of them named with "Nord"
    When the admin lists the hospital records searching "nord"
    Then the page shows 3 rows out of 3

  Scenario: La suppression demande une confirmation
    Given a hospital "NORD" exists
    And the admin is signed in on the console
    When the admin opens the deletion of the hospital "NORD"
    Then the deletion asks for confirmation and keeps the hospital "NORD"
    When the admin confirms the deletion
    Then no hospital "NORD" is stored

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle (création)
    When the admin saves a hospital "NORD" named "Hôpital Nord"
    Then the audit holds "hospital.created" for "NORD"

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle (modification)
    Given a hospital "NORD" exists
    When the admin edits the hospital "NORD" setting name "Hôpital du Nord" and city "Lille"
    Then the audit holds "hospital.updated" for "NORD" changing "name,city"

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle (sans audit, rien n'est écrit)
    Given the audit log is down
    When the admin saves a hospital "NORD" named "Hôpital Nord"
    Then the save fails
    And no hospital "NORD" is stored

  Scenario Outline: Règle §4 : la disponibilité est en heure locale de l'hôpital, donc changer son fuseau recalcule les créneaux de ses praticiens dans la même écriture (<case>)
    Given a hospital "NORD" exists
    And a department "CARD" exists in hospital "NORD"
    And a clinician profile in department "CARD"
    When the admin edits the hospital "NORD" setting time zone "<zone>"
    Then the slots of that profile are <refreshed>

 Examples:
  | case | zone | refreshed |
  | fuseau changé | America/New_York | refreshed |
  | fuseau inchangé | Europe/Paris | left as they are |
