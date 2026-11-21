Feature: Les créneaux d'un département réunissent ceux de ses praticiens
  En tant que patient connecté
  Je veux obtenir les créneaux libres d'un type sans nommer de praticien
  Afin que je voie tous les horaires possibles du département

  Background:
    Given a department in a hospital of time zone "Europe/Paris"
    And an active clinician "A" in that department
    And an active clinician "B" in that department
    And an active appointment type of 30 minutes with a 10-minute buffer
    And "A" has a rule on weekday 1 from "09:00" to "10:00" every 30 minutes
    And "B" has a rule on weekday 1 from "09:30" to "10:30" every 30 minutes

  Scenario: Sans praticien nommé, GET /slots renvoie l'union des créneaux libres de chaque praticien actif du département du type, une seule entrée par début
    When the department's slots are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then the slots start at "09:00, 09:30, 10:00"

  Scenario: Un praticien inactif n'y apporte aucun créneau
    Given the clinician "B" is inactive
    When the department's slots are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then the slots start at "09:00, 09:30"

  Scenario: Les règles du calcul par praticien, dont le plafond de 31 jours, s'appliquent à l'identique
    When the department's slots are asked from "2026-11-23 00:00" to "2026-12-25 00:00"
    Then the request is refused as "invalid_input"

  Scenario: Les règles du calcul par praticien, dont le plafond de 31 jours, s'appliquent à l'identique (une absence retire le créneau)
    Given "B" is off from "2026-11-23 10:00" to "2026-11-23 10:30"
    When the department's slots are asked from "2026-11-23 00:00" to "2026-11-24 00:00"
    Then the slots start at "09:00, 09:30"
