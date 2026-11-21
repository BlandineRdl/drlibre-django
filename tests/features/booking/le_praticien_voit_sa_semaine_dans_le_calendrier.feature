Feature: Le praticien voit sa semaine dans le calendrier
  En tant que praticien
  Je veux une grille de ma semaine
  Afin que je repère d'un coup d'œil mes RDV et mes absences

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And the agenda names the type "Consultation" coloured "#336699" and each room
    And a patient "Marie Curie"
    And a patient "Paul Valéry"
    And the signed-in clinician is "A"

  Scenario: Les RDV actifs (ni `CANCELLED` ni `NO_SHOW`) apparaissent dans la couleur de leur type ; les RDV annulés ou absents n'apparaissent pas.
    Given "Marie Curie" has a "COMPLETED" appointment with "A" at "2026-11-16 08:00" in room "R1"
    And "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-17 09:00" in room "R1"
    And "Paul Valéry" has a "CHECKED_IN" appointment with "A" at "2026-11-18 10:00" in room "R2"
    And "Paul Valéry" has a "CANCELLED" appointment with "A" at "2026-11-19 09:00" in room "R1"
    And "Marie Curie" has a "NO_SHOW" appointment with "A" at "2026-11-20 08:00" in room "R1"
    And "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-23 09:00" in room "R1"
    When the clinician opens the week of "2026-11-20"
    Then the week starts on "2026-11-16" in the zone "Europe/Paris"
    And the week shows the appointments at "2026-11-16 08:00, 2026-11-17 09:00, 2026-11-18 10:00" coloured "#336699"

  Scenario: La grille couvre la semaine de 07:00 à 19:00 par tranches de 30 minutes.
    When the clinician opens the calendar of the week of "2026-11-18"
    Then the calendar shows 7 days in rows from "07:00" to "19:00" by 30 minutes

  Scenario: Les absences du praticien apparaissent en blocs.
    Given "A" is away from "2026-11-17 08:00" to "2026-11-17 09:30"
    When the clinician opens the calendar of the week of "2026-11-18"
    Then the calendar shows the absence only on "2026-11-17" at "09:00, 09:30, 10:00"

  Scenario: Seuls les RDV et absences du praticien connecté apparaissent, aux heures du fuseau de l'hôpital, indiqué sur la page. (RDV)
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-15 23:30" in room "R1"
    And "Paul Valéry" has a "BOOKED" appointment with "A" at "2026-11-22 23:30" in room "R1"
    And "Paul Valéry" has a "BOOKED" appointment with "B" at "2026-11-18 09:00" in room "R2"
    When the clinician opens the calendar of the week of "2026-11-18"
    Then the week starts on "2026-11-16" in the zone "Europe/Paris"
    And the week shows the appointments at "2026-11-15 23:30" coloured "#336699"
    And every shown appointment is with "A"
    And the calendar names the zone "Europe/Paris"

  Scenario: Seuls les RDV et absences du praticien connecté apparaissent, aux heures du fuseau de l'hôpital, indiqué sur la page. (absences)
    Given "A" is away from "2026-11-18 13:00" to "2026-11-18 14:00"
    And "B" is away from "2026-11-19 08:00" to "2026-11-19 09:00"
    When the clinician opens the calendar of the week of "2026-11-18"
    Then the calendar shows the absence only on "2026-11-18" at "14:00, 14:30"
    And the calendar names the zone "Europe/Paris"
