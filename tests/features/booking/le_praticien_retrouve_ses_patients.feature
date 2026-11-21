Feature: Le praticien retrouve ses patients
  En tant que praticien
  Je veux la liste des patients que je suis
  Afin que je retrouve vite un patient et ses dates de visite

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And the agenda names the type "Consultation" coloured "#336699" and each room
    And a patient "Marie Curie"
    And a patient "Marc Bloch"
    And a patient "Paul Valéry"
    And a patient "Martin Nadaud"
    And the signed-in clinician is "A"

  Scenario: La liste contient les patients qui ont au moins un RDV avec le praticien connecté, et eux seuls.
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-25 09:00" in room "R1"
    And "Marc Bloch" has a "CANCELLED" appointment with "A" at "2026-11-24 09:00" in room "R1"
    And "Paul Valéry" has a "BOOKED" appointment with "B" at "2026-11-25 09:00" in room "R2"
    When the clinician lists their patients
    Then the patients shown are "Marc Bloch, Marie Curie"

  Scenario: Chaque patient montre son téléphone, sa dernière visite et sa prochaine visite.
    Given "Marie Curie" has a "COMPLETED" appointment with "A" at "2026-11-10 09:00" in room "R1"
    And "Marie Curie" has a "COMPLETED" appointment with "A" at "2026-11-13 09:00" in room "R1"
    And "Marie Curie" has a "NO_SHOW" appointment with "A" at "2026-11-18 09:00" in room "R1"
    And "Marie Curie" has a "CANCELLED" appointment with "A" at "2026-11-23 09:00" in room "R1"
    And "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-25 09:00" in room "R1"
    And "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-27 09:00" in room "R1"
    And "Marc Bloch" has a "CHECKED_IN" appointment with "A" at "2026-11-20 08:00" in room "R1"
    When the clinician lists their patients
    Then "Marie Curie" shows the phone "0600000000", last visit "2026-11-13 09:00" and next visit "2026-11-25 09:00"
    And "Marc Bloch" shows the phone "0600000000", last visit "none" and next visit "none"

  Scenario: Une recherche par nom filtre la liste.
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-25 09:00" in room "R1"
    And "Marc Bloch" has a "BOOKED" appointment with "A" at "2026-11-26 09:00" in room "R1"
    And "Paul Valéry" has a "BOOKED" appointment with "A" at "2026-11-27 09:00" in room "R1"
    And "Martin Nadaud" has a "BOOKED" appointment with "B" at "2026-11-25 09:00" in room "R2"
    When the clinician lists their patients searching "mar"
    Then the patients shown are "Marc Bloch, Marie Curie"
