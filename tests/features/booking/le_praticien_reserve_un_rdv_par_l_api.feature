Feature: Le praticien réserve un RDV par l'API
  En tant que praticien
  Je veux réserver par `POST /appointments` un RDV dans mon agenda pour un patient actif
  Afin que je planifie un suivi sans passer par le patient

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And the signed-in clinician is "A"
    And "A" is free at "2026-11-20 10:30"

  Scenario: Le RDV est toujours placé dans l'agenda du praticien connecté ; une requête qui nomme un autre praticien est refusée. (agenda du praticien connecté)
    When the clinician books the patient at "2026-11-20 10:30"
    Then the appointment is with "A"
    And the appointment belongs to the signed-in patient

  Scenario: Le RDV est toujours placé dans l'agenda du praticien connecté ; une requête qui nomme un autre praticien est refusée. (autre praticien nommé)
    When the clinician books the patient at "2026-11-20 10:30" with "B"
    Then the booking is refused as "forbidden"
    And nothing was written

  Scenario: La requête nomme un patient actif ; la fin est calculée à partir de la durée du type. (patient actif)
    When the clinician books the patient at "2026-11-20 10:30"
    Then the appointment ends 30 minutes after it starts

  Scenario: La requête nomme un patient actif ; la fin est calculée à partir de la durée du type. (patient inactif)
    Given the patient account is inactive
    When the clinician books the patient at "2026-11-20 10:30"
    Then the booking is refused as "forbidden"
    And nothing was written

  Scenario: La requête nomme un patient actif ; la fin est calculée à partir de la durée du type. (patient omis)
    When the clinician books at "2026-11-20 10:30" without naming a patient
    Then the booking is refused as "invalid_input"
    And the refusal names the field "patient"
    And nothing was written

  Scenario: Le type doit être actif et du département du praticien ; sinon `not_found`. (type inactif)
    Given the appointment type is inactive
    When the clinician books the patient at "2026-11-20 10:30"
    Then the booking is refused as "not_found"
    And nothing was written

  Scenario: Le type doit être actif et du département du praticien ; sinon `not_found`. (type d'un autre département)
    Given the clinician "A" is in another department
    When the clinician books the patient at "2026-11-20 10:30"
    Then the booking is refused as "not_found"
    And nothing was written

  Scenario: Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou d'une salle nommée renvoient `conflict`. (hors créneau)
    When the clinician books the patient at "2026-11-20 13:00"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "outside_availability"
    And nothing was written

  Scenario: Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou d'une salle nommée renvoient `conflict`. (praticien occupé)
    Given "A" has an active appointment from "2026-11-20 10:45" to "2026-11-20 11:15"
    When the clinician books the patient at "2026-11-20 10:30"
    Then the booking is refused as "conflict"
    And the refusal names the resources "clinician"

  Scenario: Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou d'une salle nommée renvoient `conflict`. (patient occupé)
    Given the patient has an active appointment with "B" from "2026-11-20 10:45" to "2026-11-20 11:15"
    When the clinician books the patient at "2026-11-20 10:30"
    Then the booking is refused as "conflict"
    And the refusal names the resources "patient"

  Scenario: Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou d'une salle nommée renvoient `conflict`. (salle nommée occupée)
    Given the room "R2" is used by someone else from "2026-11-20 10:45" to "2026-11-20 11:15"
    When the clinician books the patient at "2026-11-20 10:30" in room "R2"
    Then the booking is refused as "conflict"
    And the refusal names the resources "room"

  Scenario: Le délai de 120 minutes, la limite de 3 réservations en ligne et la réservabilité en ligne du type ne s'appliquent pas.
    Given the appointment type is not bookable online
    And the patient has 3 open online bookings
    When the clinician books the patient at "2026-11-20 10:30"
    Then the appointment is "BOOKED" for "STAFF"

  Scenario: Une salle nommée doit être active ; sans salle nommée, un type qui en exige une reçoit la salle par défaut si libre, sinon la première salle libre du département, sinon `no_room_available`. (salle nommée inactive)
    Given an inactive room "R3" in that department
    When the clinician books the patient at "2026-11-20 10:30" in room "R3"
    Then the booking is refused as "not_found"
    And nothing was written

  Scenario: Une salle nommée doit être active ; sans salle nommée, un type qui en exige une reçoit la salle par défaut si libre, sinon la première salle libre du département, sinon `no_room_available`. (salle nommée pour un type sans salle)
    Given the appointment type needs no room
    When the clinician books the patient at "2026-11-20 10:30" in room "R2"
    Then the booking is refused as "invalid_input"
    And the refusal names the field "room"
    And nothing was written

  Scenario: Une salle nommée doit être active ; sans salle nommée, un type qui en exige une reçoit la salle par défaut si libre, sinon la première salle libre du département, sinon `no_room_available`. (salle nommée libre)
    When the clinician books the patient at "2026-11-20 10:30" in room "R2"
    Then the appointment is "BOOKED" in room "R2"

  Scenario Outline: Une salle nommée doit être active ; sans salle nommée, un type qui en exige une reçoit la salle par défaut si libre, sinon la première salle libre du département, sinon `no_room_available`. (<case>)
    Given the rooms "<busy>" are used by someone else from "2026-11-20 10:30" to "2026-11-20 11:00"
    When the clinician books the patient at "2026-11-20 10:30"
    Then the appointment is "BOOKED" in room "<room>"

    Examples:
      | case                 | busy | room |
      | salle par défaut     | R2   | R1   |
      | première salle libre | R1   | R2   |

  Scenario: Une salle nommée doit être active ; sans salle nommée, un type qui en exige une reçoit la salle par défaut si libre, sinon la première salle libre du département, sinon `no_room_available`. (aucune salle libre)
    Given the rooms "R1, R2" are used by someone else from "2026-11-20 10:30" to "2026-11-20 11:00"
    When the clinician books the patient at "2026-11-20 10:30"
    Then the booking is refused as "no_room_available"
    And nothing was written

  Scenario: Le RDV est créé `BOOKED` avec la source `STAFF` ; le patient reçoit une notification « RDV réservé » et un email.
    When the clinician books the patient at "2026-11-20 10:30"
    Then the appointment is "BOOKED" for "STAFF"
    And the patient has one "RDV réservé" notification about the booking
    And a confirmation was queued

  Scenario: La réservation laisse une entrée d'audit sans donnée personnelle.
    When the clinician books the patient at "2026-11-20 10:30"
    Then the audit entry "booking.appointment_booked" has the clinician as actor and holds only "appointment_type_id, clinician_id, email_domain, room_id, source"
