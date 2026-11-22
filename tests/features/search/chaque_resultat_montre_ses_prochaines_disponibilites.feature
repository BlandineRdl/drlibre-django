Feature: Chaque résultat montre ses prochaines disponibilités

  Background:
    Given the hospital "Hôpital Nord" in "Lille" at 50.63 3.06
    And the department "Cardiologie" of "Hôpital Nord" offers "Consultation cardio" of 20 minutes online
    And the clinician "Dr Alice Martin" of "Cardiologie" in "Cardiologie"
    And the clinician "Dr Bruno Petit" of "Cardiologie" in "Cardiologie"

  Scenario: Un praticien montre ses 3 prochains débuts libres ; un hôpital, son premier créneau libre et le nombre de praticiens qui ont un créneau libre dans l'horizon ; une spécialité, son premier créneau libre parmi tous ses praticiens.
    Given "Dr Alice Martin" is free at "2026-11-23 09:00, 09:20, 09:40, 10:00"
    And "Dr Bruno Petit" is free at "2026-11-23 08:40"
    When the visitor opens "/api/v1/search/providers"
    Then "Dr Alice Martin" shows the next starts "2026-11-23 09:00, 2026-11-23 09:20, 2026-11-23 09:40"
    When the visitor opens "/api/v1/search/hospitals"
    Then "Hôpital Nord" shows the first start "2026-11-23 08:40"
    And "Hôpital Nord" shows "providers_with_slots" equal to "2"
    When the visitor opens "/api/v1/search/specialties"
    Then "Cardiologie" shows the first start "2026-11-23 08:40"

  Scenario: Sans filtre de type, les créneaux sont ceux du type actif réservable en ligne le plus court du département du praticien, et le résultat nomme ce type.
    Given the department "Cardiologie" of "Hôpital Nord" offers "Bilan long" of 60 minutes online
    And the department "Cardiologie" of "Hôpital Nord" offers "Appel rapide" of 5 minutes by phone only
    And the department "Cardiologie" of "Hôpital Nord" offers "Ancien flash" of 10 minutes online
    And the type "Ancien flash" is inactive
    And "Dr Alice Martin" is free at "2026-11-23 11:00" for "Bilan long"
    And "Dr Alice Martin" is free at "2026-11-23 09:00" for "Consultation cardio"
    When the visitor opens "/api/v1/search/providers"
    Then "Dr Alice Martin" shows the next starts "2026-11-23 09:00"
    And "Dr Alice Martin" shows the type "Consultation cardio"
    When the visitor opens "/"
    Then the page says "Consultation cardio 20 min"

  Scenario Outline: Les créneaux sont cherchés de maintenant plus 120 minutes jusqu'à 90 jours devant.
    Given "Dr Alice Martin" is free at "<start>"
    When the visitor opens "/api/v1/search/providers?q=alice"
    Then "Dr Alice Martin" shows <result>

    Examples:
      | start            | result                                          |
      | 2026-11-20 11:30 | no availability                                 |
      | 2026-11-20 13:00 | the next starts "2026-11-20 13:00"              |
      | 2027-02-18 09:00 | the next starts "2027-02-18 09:00"              |
      | 2027-02-19 09:00 | no availability                                 |

  Scenario: Un résultat sans créneau dans l'horizon reste listé, après ceux qui en ont, avec le texte « Aucune disponibilité dans les 90 prochains jours ».
    Given "Dr Bruno Petit" is free at "2026-11-24 09:00"
    When the visitor opens "/api/v1/search/providers"
    Then the listed names are "Dr Bruno Petit, Dr Alice Martin"
    And "Dr Alice Martin" shows no availability
    When the visitor opens "/"
    Then the page says "Aucune disponibilité dans les 90 prochains jours"

  Scenario: Par défaut, les résultats sont triés par disponibilité la plus proche.
    Given "Dr Alice Martin" is free at "2026-11-25 09:00"
    And "Dr Bruno Petit" is free at "2026-11-23 09:00"
    And the clinician "Dr Chloé Durand" of "Cardiologie" in "Cardiologie"
    When the visitor opens "/api/v1/search/providers"
    Then the listed names are "Dr Bruno Petit, Dr Alice Martin, Dr Chloé Durand"

  Scenario Outline: Les créneaux montrés sont exactement ceux que la réservation accepterait au moment où la liste est construite.
    Given "Dr Alice Martin" is free at "2026-11-23 09:00, 09:20"
    And a hold on "Dr Alice Martin" at "2026-11-23 09:00" with <minutes> minutes left
    When the visitor opens "/api/v1/search/providers"
    Then "Dr Alice Martin" shows the next starts "<search>"
    When the visitor opens "/providers/[id:Dr Alice Martin]?week=2026-11-23"
    Then the page <page>
    When the visitor opens "/api/v1/slots?type=[type:Consultation cardio]&clinician=[id:Dr Alice Martin]&start=2026-11-23T00:00:00Z&end=2026-11-24T00:00:00Z"
    Then the free slots start at "<slots>" UTC

    Examples:
      | minutes | search                                     | page                       | slots       |
      | 10      | 2026-11-23 09:20                           | never says "09:00"         | 08:20       |
      | -1      | 2026-11-23 09:00, 2026-11-23 09:20         | says "09:00"               | 08:00,08:20 |

  Scenario: Règle §6.2 : un créneau dont toutes les salles du département sont prises n'est pas proposé
    Given the type "Consultation cardio" needs a room
    And the room "Box 1" of "Cardiologie"
    And "Dr Alice Martin" is free at "2026-11-23 09:00, 09:20"
    And "Dr Bruno Petit" has an appointment in "Box 1" at "2026-11-23 09:00"
    When the visitor opens "/api/v1/search/providers"
    Then "Dr Alice Martin" shows the next starts "2026-11-23 09:20"
    When the visitor opens "/api/v1/search/hospitals"
    Then "Hôpital Nord" shows the first start "2026-11-23 09:20"
    When the visitor opens "/providers/[id:Dr Alice Martin]?week=2026-11-23"
    Then the page never says "09:00"
    When the visitor opens "/api/v1/slots?type=[type:Consultation cardio]&clinician=[id:Dr Alice Martin]&start=2026-11-23T00:00:00Z&end=2026-11-24T00:00:00Z"
    Then the free slots start at "08:20" UTC

  Scenario: Règle §6.2 : un créneau reste proposé tant qu'une salle active du département est libre
    Given the type "Consultation cardio" needs a room
    And the room "Box 1" of "Cardiologie"
    And the room "Box 2" of "Cardiologie"
    And "Dr Alice Martin" is free at "2026-11-23 09:00, 09:20"
    And "Dr Bruno Petit" has an appointment in "Box 1" at "2026-11-23 09:00"
    When the visitor opens "/api/v1/search/providers"
    Then "Dr Alice Martin" shows the next starts "2026-11-23 09:00, 2026-11-23 09:20"
    When the visitor opens "/api/v1/slots?type=[type:Consultation cardio]&clinician=[id:Dr Alice Martin]&start=2026-11-23T00:00:00Z&end=2026-11-24T00:00:00Z"
    Then the free slots start at "08:00,08:20" UTC

  Scenario: Les heures sont dans le fuseau de l'hôpital, que la page nomme.
    Given the hospital "Hôpital Réunion" in "Saint-Denis" in the time zone "Indian/Reunion"
    And the department "Pédiatrie" of "Hôpital Réunion" offers "Consultation pédiatrie" of 30 minutes online
    And the clinician "Dr Léa Hoarau" of "Pédiatrie" in "Pédiatrie"
    And "Dr Léa Hoarau" is free at "2026-11-23 09:00"
    When the visitor opens "/?q=hoarau"
    Then the page says "lun. 23/11 09:00"
    And the page says "Heure de Reunion"
    When the visitor opens "/api/v1/search/providers?q=hoarau"
    Then the zone of every start is +04:00
