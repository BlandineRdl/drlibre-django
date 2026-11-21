Feature: Les plages du praticien donnent ses créneaux libres
  En tant que praticien
  Je veux obtenir les créneaux libres que mes plages ouvrent pour un type de RDV de mon département
  Afin que la recherche et chaque réservation reposent sur le même calcul

  Background:
    Given a department in a hospital of time zone "Europe/Paris"
    And an active clinician "A" in that department
    And an active appointment type of 30 minutes with a 10-minute buffer

  Scenario: GET /slots prend un type, un praticien et une période ; sans session, il répond unauthenticated (type, praticien et période)
    Given "A" has a rule on weekday 1 from "09:00" to "10:00" every 30 minutes
    When the slots of "A" are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then the slots start at "09:00, 09:30"

  Scenario: GET /slots prend un type, un praticien et une période ; sans session, il répond (E3 ouvre cette route : 200 sans session)
    When the slots of "A" are asked through the API without a session
    Then the API answers 200 "slots"

  Scenario: Pour chaque jour local de la période, chaque plage valable ce jour-là propose un début à son heure de début puis à chaque pas, tant que le début plus la durée du type ne dépasse pas sa fin ; chaque créneau dure la durée du type
    Given "A" has a rule on weekday 1 from "09:00" to "12:00" every 15 minutes
    When the slots of "A" are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then the slots start at "09:00, 09:15, 09:30, 09:45, 10:00, 10:15, 10:30, 10:45, 11:00, 11:15, 11:30"
    And every slot lasts 30 minutes

  Scenario: Pour chaque jour local de la période, chaque plage valable ce jour-là propose un début à son heure de début puis à chaque pas, tant que le début plus la durée du type ne dépasse pas sa fin ; chaque créneau dure la durée du type (hors de sa validité)
    Given "A" has a rule on weekday 1 from "09:00" to "10:00" every 30 minutes, valid from "2026-11-24"
    When the slots of "A" are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then no slot is returned

  Scenario Outline: Un créneau qui commence avant la période, finit après elle ou commence dans le passé n'est pas renvoyé (<case>)
    Given "A" has a rule on weekday <weekday> from "09:00" to "12:00" every 30 minutes
    When the slots of "A" are asked from "<from>" to "<to>"
    Then the slots start at "<starts>"

    Examples:
      | case                         | weekday | from             | to               | starts                     |
      | avant la période             | 1       | 2026-11-23 09:20 | 2026-11-24 00:00 | 09:30, 10:00, 10:30, 11:00, 11:30 |
      | après la période             | 1       | 2026-11-23 00:00 | 2026-11-23 10:20 | 09:00, 09:30               |
      | dans le passé                | 5       | 2026-11-20 00:00 | 2026-11-21 00:00 | 11:00, 11:30               |

  Scenario: Les débuts renvoyés sont uniques et triés par ordre croissant
    Given "A" has a rule on weekday 1 from "10:00" to "11:00" every 30 minutes
    And "A" has a rule on weekday 1 from "09:00" to "11:00" every 30 minutes
    When the slots of "A" are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then the slots start at "09:00, 09:30, 10:00, 10:30"

  Scenario: Une période de plus de 31 jours est refusée en invalid_input
    Given "A" has a rule on weekday 1 from "09:00" to "10:00" every 30 minutes
    When the slots of "A" are asked from "2026-11-23 00:00" to "2026-12-25 00:00"
    Then the request is refused as "invalid_input"

  Scenario: Une période de plus de 31 jours est refusée en invalid_input (31 jours acceptés)
    Given "A" has a rule on weekday 1 from "09:00" to "10:00" every 30 minutes
    When the slots of "A" are asked from "2026-11-23 00:00" to "2026-12-24 00:00"
    Then 10 slots are returned

  Scenario: Une période de plus de 31 jours est refusée en invalid_input (31 jours locaux à travers le retour à l'heure d'hiver)
    Given today is "2026-10-01"
    And "A" has a rule on weekday 1 from "09:00" to "10:00" every 30 minutes
    When the slots of "A" are asked from "2026-10-05 00:00" to "2026-11-05 00:00"
    Then 10 slots are returned

  Scenario Outline: La semaine du changement d'heure, une plage 09:00–12:00 donne toujours un premier créneau à 09:00 heure locale de l'hôpital (<case>)
    Given today is "<today>"
    And "A" has a rule on weekday 0 from "09:00" to "12:00" every 15 minutes
    When the slots of "A" are asked from "<day> 00:00" to "<next> 00:00"
    Then the first slot starts at "<day> 09:00"
    And 11 slots are returned

    Examples:
      | case                     | today      | day        | next       |
      | passage à l'heure d'été  | 2026-03-23 | 2026-03-29 | 2026-03-30 |
      | retour à l'heure d'hiver | 2026-10-19 | 2026-10-25 | 2026-10-26 |

  Scenario Outline: Une plage créée, modifiée ou supprimée change les créneaux renvoyés dès la réponse qui l'enregistre (<case>)
    Given "A" has a rule on weekday 1 from "09:00" to "10:00" every 30 minutes
    When "A" <change>
    And the slots of "A" are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then the slots start at "<starts>"

    Examples:
      | case      | change                                                          | starts              |
      | créée     | adds a rule on weekday 1 from "14:00" to "15:00" every 30 minutes | 09:00, 09:30, 14:00, 14:30 |
      | modifiée  | moves the rule to "10:00" until "11:00"                                | 10:00, 10:30        |
      | supprimée | deletes the rule                                                |                     |

  Scenario: Les créneaux sont connus jusqu'à 90 jours devant ; cet horizon avance chaque jour sans intervention (90 jours devant)
    Given "A" has a rule every day from "09:00" to "09:30" every 30 minutes
    When the slots of "A" are asked from "2027-02-17 00:00" to "2027-02-21 00:00"
    Then the slots run on "2027-02-17, 2027-02-18"

 Scenario: Les créneaux sont connus jusqu'à 90 jours devant ; cet horizon avance chaque jour sans intervention (le lendemain)
  Given "A" has a rule every day from "09:00" to "09:30" every 30 minutes
  When a day passes and the daily job runs
  And the slots of "A" are asked from "2027-02-17 00:00" to "2027-02-21 00:00"
  Then the slots run on "2027-02-17, 2027-02-18, 2027-02-19"

  Scenario Outline: Règle §4 : un type ou un praticien inconnu ou inactif donne not_found (<case>)
    Given <situation>
    When the slots of "<clinician>" are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then the request is refused as "not_found"

    Examples:
      | case                         | situation                                         | clinician |
      | type inconnu                 | the appointment type is unknown                   | A         |
      | type inactif                 | the appointment type is inactive                  | A         |
      | praticien inconnu            | the clinician "Z" is unknown                      | Z         |
      | praticien inactif            | the clinician "A" is inactive                     | A         |
      | praticien d'un autre service | an active clinician "B" in another department     | B         |
