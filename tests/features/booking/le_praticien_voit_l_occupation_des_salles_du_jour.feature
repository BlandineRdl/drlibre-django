Feature: Le praticien voit l'occupation des salles du jour
  En tant que praticien
  Je veux une frise du jour des salles de mon département
  Afin que je sache quelles salles sont prises et quand

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And the agenda names the type "Consultation" coloured "#336699" and each room
    And a patient "Marie Curie"
    And a patient "Paul Valéry"
    And the signed-in clinician is "A"

  Scenario: La frise couvre 07:00 à 19:00 et liste les salles actives du département du praticien. (salles listées)
    Given an inactive room "R3" in that department
    When the clinician opens the rooms of the day "2026-11-20"
    Then the rooms shown are "R1, R2" on "2026-11-20" in the zone "Europe/Paris"

  Scenario: Ses propres RDV affichent le nom du patient ; ceux des autres praticiens affichent seulement « Occupied ».
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-20 13:00" in room "R1"
    And "Paul Valéry" has a "CHECKED_IN" appointment with "B" at "2026-11-20 13:00" in room "R2"
    And "Paul Valéry" has a "CANCELLED" appointment with "B" at "2026-11-20 15:00" in room "R1"
    And "Marie Curie" has a "NO_SHOW" appointment with "A" at "2026-11-20 16:00" in room "R2"
    When the clinician opens the rooms of the day "2026-11-20"
    Then room "R1" is taken at "2026-11-20 13:00" by "Marie Curie"
    And room "R2" is taken at "2026-11-20 13:00" by "Occupied"
    And the rooms are taken only at "2026-11-20 13:00, 2026-11-20 13:00"

  Scenario: Les heures sont affichées dans le fuseau de l'hôpital, indiqué sur la page.
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-19 23:30" in room "R1"
    And "Paul Valéry" has a "BOOKED" appointment with "B" at "2026-11-20 23:30" in room "R2"
    When the clinician opens the rooms of the day "2026-11-20"
    Then the rooms shown are "R1, R2" on "2026-11-20" in the zone "Europe/Paris"
    And the rooms are taken only at "2026-11-19 23:30"
