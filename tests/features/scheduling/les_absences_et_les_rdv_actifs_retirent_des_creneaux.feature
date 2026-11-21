Feature: Les absences et les RDV actifs retirent des créneaux
  En tant que praticien
  Je veux que mes absences et mes RDV actifs retirent les créneaux qu'ils chevauchent
  Afin qu'aucun créneau proposé ne soit déjà occupé

  Background:
    Given a department in a hospital of time zone "Europe/Paris"
    And an active clinician "A" in that department
    And an active appointment type of 30 minutes with a 10-minute buffer
    And "A" has a rule on weekday 1 from "09:00" to "12:00" every 10 minutes

  Scenario: Un créneau qui chevauche une absence du praticien n'est pas renvoyé
    Given "A" is off from "2026-11-23 10:00" to "2026-11-23 11:00"
    When the slots of "A" are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then the slots start at "09:00, 09:10, 09:20, 09:30, 11:00, 11:10, 11:20, 11:30"

  Scenario: Un créneau qui chevauche un RDV actif du praticien, prolongé à sa fin du buffer du type demandé, n'est pas renvoyé
    Given "A" has a "BOOKED" appointment from "2026-11-23 10:00" to "2026-11-23 10:30"
    When the slots of "A" are asked from "2026-11-23 09:20" to "2026-11-23 11:20"
    Then the slots start at "09:20, 09:30, 10:40, 10:50"

  Scenario Outline: Un RDV `CANCELLED` ou `NO_SHOW` ne retire aucun créneau (<case>)
    Given "A" has a "<status>" appointment from "2026-11-23 10:00" to "2026-11-23 10:30"
    When the slots of "A" are asked from "2026-11-23 09:50" to "2026-11-23 10:50"
    Then the slots start at "09:50, 10:00, 10:10, 10:20"

    Examples:
      | case    | status    |
      | annulé  | CANCELLED |
      | absent  | NO_SHOW   |

  Scenario Outline: Une absence créée ou supprimée change les créneaux renvoyés dès la réponse qui l'enregistre ; un RDV qui devient actif ou cesse de l'être aussi (<case>)
    Given <before>
    When <change>
    And the slots of "A" are asked from "2026-11-23 09:50" to "2026-11-23 10:50"
    Then the slots start at "<starts>"

    Examples:
      | case               | before                                                                       | change                                                     | starts                  |
      | absence créée      | "A" has no time off                                                          | "A" is off from "2026-11-23 10:00" to "2026-11-23 10:10"    | 10:10, 10:20            |
      | absence supprimée  | "A" is off from "2026-11-23 10:00" to "2026-11-23 10:10"                     | the time off of "A" is deleted                              | 09:50, 10:00, 10:10, 10:20 |
      | RDV devenu actif   | "A" has a "CANCELLED" appointment from "2026-11-23 10:00" to "2026-11-23 10:30" | the appointment of "A" becomes "BOOKED"                  |                         |
      | RDV qui cesse      | "A" has a "BOOKED" appointment from "2026-11-23 10:00" to "2026-11-23 10:30"    | the appointment of "A" becomes "NO_SHOW"                 | 09:50, 10:00, 10:10, 10:20 |
