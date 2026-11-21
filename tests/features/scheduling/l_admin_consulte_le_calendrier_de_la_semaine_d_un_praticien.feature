Feature: L'admin consulte le calendrier de la semaine d'un praticien
  En tant que admin
  Je veux ouvrir le calendrier de la semaine de chaque praticien
  Afin que je contrôle ses disponibilités sans pouvoir les modifier

  Background:
    Given a hospital of time zone "America/Montreal" with the clinicians "Dr A" and "Dr B"
    And today is "2026-11-20"
    And the admin is signed in on the console

  Scenario: Chaque praticien a un calendrier de la semaine, en lecture seule : aucune action d'écriture n'y est proposée
    Given "Dr A" saved a rule on weekday "1" from "09:00" to "10:00"
    When the admin opens the week of "Dr A" starting "2026-11-23"
    Then the week shows "Disponible" on "Lun 23/11" at "09:00, 09:30"
    And the week offers no write action

  Scenario: Chaque praticien a un calendrier de la semaine, en lecture seule : aucune action d'écriture n'y est proposée (praticien sans plage)
    When the admin opens the week of "Dr B" starting "2026-11-23"
    Then the week shows no "Disponible" cell
    And the week offers no write action

  Scenario: Les heures sont dans le fuseau de l'hôpital du praticien, que la page nomme
    Given "Dr A" saved a rule on weekday "2" from "09:00" to "12:00"
    And "Dr A" recorded a time off from "2026-11-24T10:00" to "2026-11-24T11:00"
    When the admin opens the week of "Dr A" starting "2026-11-23"
    Then the page names the time zone "America/Montreal"
    And the week shows "Absence" on "Mar 24/11" at "10:00, 10:30"
    And the week shows "Disponible" on "Mar 24/11" at "09:00, 09:30, 11:00, 11:30"
