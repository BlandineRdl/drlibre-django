Feature: Un patient connecté réserve sans ressaisir ses informations
  En tant que patient connecté
  Je veux réserver depuis la recherche ou une page publique sans saisie ni code
  Afin que je reprenne un RDV en quelques clics

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And "A" and "B" are free at "2026-11-23 09:00"

  Scenario: Un patient connecté qui choisit un créneau passe directement de son choix à la confirmation, sans saisie de ses informations ni code
    When the patient books "A" at "2026-11-23 09:00"
    Then the appointment is "BOOKED" for "ONLINE"

  Scenario: Il réserve pour lui-même seulement : son identité vient de la session, et il ne peut nommer ni un autre patient ni une salle (lui-même)
    When the patient books "A" at "2026-11-23 09:00" naming themself
    Then the appointment belongs to the signed-in patient

  Scenario: Il réserve pour lui-même seulement : son identité vient de la session, et il ne peut nommer ni un autre patient ni une salle (autre patient)
    When the patient books "A" at "2026-11-23 09:00" naming another patient
    Then the booking is refused as "forbidden"
    And nothing was written

  Scenario: Il réserve pour lui-même seulement : son identité vient de la session, et il ne peut nommer ni un autre patient ni une salle (salle)
    When the patient books "A" at "2026-11-23 09:00" in room "R2"
    Then the booking is refused as "forbidden"
    And nothing was written

  Scenario: `POST /appointments` réserve pour le patient connecté ; sans praticien nommé, il réserve le premier disponible (praticien nommé)
    When the patient posts the booking at "2026-11-23T09:00:00Z" with "A"
    Then the API answers 201 with an appointment with "A"
    And the appointment is "BOOKED" for "ONLINE"

  Scenario: `POST /appointments` réserve pour le patient connecté ; sans praticien nommé, il réserve le premier disponible (premier disponible)
    Given "A" was assigned at "2026-11-19 10:00"
    When the patient posts the booking at "2026-11-23T09:00:00Z" without a clinician
    Then the appointment is "BOOKED" for "ROUND_ROBIN"
    And the appointment is with "B"
    And the last assignment of "B" is "2026-11-20 10:00"

  Scenario: La même page de confirmation et le même email de confirmation suivent la réservation (page de confirmation)
    Given the public pages know the type and "A"
    When the patient confirms "A" at "2026-11-23T09:00:00Z" on the booking page
    Then the confirmation page shows the appointment, its calendar file and the patient's appointments

  Scenario: La même page de confirmation et le même email de confirmation suivent la réservation (email de confirmation)
    When the patient books "A" at "2026-11-23 09:00"
    Then a confirmation was queued

  Scenario: Règle §5.5 : le candidat dont la dernière affectation est la plus ancienne, pondérée, est servi en premier
    Given "A" was assigned at "2026-11-19 10:00"
    And "B" was assigned at "2026-11-10 10:00"
    When the patient books without naming a clinician at "2026-11-23 09:00"
    Then the appointment is with "B"

  Scenario: Règle §5.5 : un praticien de poids nul n'est pas candidat
    Given the clinician "B" has weight 0
    When the patient books without naming a clinician at "2026-11-23 09:00"
    Then the appointment is with "A"

  Scenario: Règle §5.5 : sans candidat, la réservation échoue faute de praticien disponible
    Given "A" and "B" are free at "2026-11-23 15:00"
    When the patient books without naming a clinician at "2026-11-23 09:30"
    Then the booking is refused as "no_clinician_available"
    And nothing was written

  Scenario: Règle §5.5 : un candidat pris entre-temps cède la place au candidat suivant
    Given "A" was assigned at "2026-11-10 10:00"
    And "B" was assigned at "2026-11-19 10:00"
    And "A" has an active appointment from "2026-11-23 09:00" to "2026-11-23 09:30"
    When the patient books without naming a clinician at "2026-11-23 09:00"
    Then the appointment is with "B"

  Scenario: Règle §5.5 : tous les candidats pris entre-temps, la réservation échoue faute de praticien disponible
    Given "A" has an active appointment from "2026-11-23 09:00" to "2026-11-23 09:30"
    And "B" has an active appointment from "2026-11-23 09:00" to "2026-11-23 09:30"
    When the patient books without naming a clinician at "2026-11-23 09:00"
    Then the booking is refused as "no_clinician_available"
    And nothing was written
