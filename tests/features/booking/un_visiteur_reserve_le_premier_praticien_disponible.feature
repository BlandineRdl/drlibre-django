Feature: Un visiteur réserve le premier praticien disponible
  En tant que visiteur
  Je veux réserver un créneau d'un département sans choisir de praticien
  Afin que j'obtienne le plus tôt possible un RDV du type voulu

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department

  Scenario: Les candidats sont les praticiens actifs du département du type qui ont un créneau libre à ce début
    Given an active clinician "C" in that department
    And an active clinician "D" in that department
    And "A" and "B" are free at "2026-11-23 09:00"
    And the clinician "B" is inactive
    And the clinician "D" is in another department
    When the visitor asks to hold the first available at "2026-11-23 09:00"
    Then the hold is on "A"

  Scenario: Un praticien jamais attribué passe en premier, puis la plus grande valeur de (temps depuis sa dernière attribution × poids) ; à égalité, le plus petit id
    Given "A" and "B" are free at "2026-11-23 09:00"
    And "A" was assigned at "2026-11-19 10:00"
    When the visitor asks to hold the first available at "2026-11-23 09:00"
    Then the hold is on "B"

  Scenario: Le praticien est choisi à la création de la réservation provisoire ; sa date de dernière attribution n'est mise à jour qu'à la réservation (choix à la réservation provisoire)
    Given "A" and "B" are free at "2026-11-23 09:00"
    And "A" was assigned at "2026-11-19 10:00"
    When the visitor asks to hold the first available at "2026-11-23 09:00"
    Then the hold is on "B"
    And no round robin assignment was recorded

  Scenario: Le praticien est choisi à la création de la réservation provisoire ; sa date de dernière attribution n'est mise à jour qu'à la réservation (mise à jour à la réservation)
    Given "A" and "B" are free at "2026-11-23 09:00"
    And "A" was assigned at "2026-11-19 10:00"
    And the visitor asks to hold the first available at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the last assignment of "B" is "2026-11-20 10:00"

  Scenario: Le RDV porte la source `ROUND_ROBIN`
    Given "A" and "B" are free at "2026-11-23 09:00"
    And the visitor asks to hold the first available at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the appointment is "BOOKED" for "ROUND_ROBIN"

  Scenario: Sans candidat, la réservation échoue en `no_clinician_available` et le visiteur en est informé
    When the visitor asks to hold the first available at "2026-11-23 09:00"
    Then the booking is refused as "no_clinician_available"
    And no hold was created

  Scenario: Règle §5.5 : un candidat pris entre-temps cède la place au candidat suivant
    Given "A" and "B" are free at "2026-11-23 09:00"
    And "A" was assigned at "2026-11-10 10:00"
    And "B" was assigned at "2026-11-19 10:00"
    And "A" has an active appointment from "2026-11-23 09:00" to "2026-11-23 09:30"
    When the visitor asks to hold the first available at "2026-11-23 09:00"
    Then the hold is on "B"

  Scenario: Règle §5.5 : tous les candidats pris entre-temps, la réservation échoue faute de praticien disponible
    Given "A" and "B" are free at "2026-11-23 09:00"
    And "A" has an active appointment from "2026-11-23 09:00" to "2026-11-23 09:30"
    And "B" has an active appointment from "2026-11-23 09:00" to "2026-11-23 09:30"
    When the visitor asks to hold the first available at "2026-11-23 09:00"
    Then the booking is refused as "no_clinician_available"
    And no hold was created
