Feature: L'admin réserve un RDV pour un patient
  En tant qu'admin
  Je veux réserver pour un patient actif, avec n'importe quel praticien
  Afin que j'aide un patient qui ne peut pas réserver lui-même

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And a signed-in admin
    And "A" is free at "2026-11-20 10:30"

  Scenario: L'assistant enchaîne type, praticien et créneau ; il ne propose pas « premier disponible » et inclut les types non réservables en ligne. (praticien nommé)
    Given the appointment type is not bookable online
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the appointment is with "A"
    And the appointment belongs to the signed-in patient

  Scenario: L'assistant enchaîne type, praticien et créneau ; il ne propose pas « premier disponible » et inclut les types non réservables en ligne. (sans praticien)
    When the admin books the patient at "2026-11-20 10:30" without naming a clinician
    Then the booking is refused as "invalid_input"
    And the refusal names the field "clinician"
    And nothing was written

  Scenario: Règle §5.2 : le patient réservé par l'admin doit être actif
    Given the patient account is inactive
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the booking is refused as "forbidden"
    And nothing was written

  Scenario: Règle §5.2 : l'admin ne réserve que pour un patient
    When the admin books "admin@example.org" at "2026-11-20 10:30" with "A"
    Then the booking is refused as "forbidden"
    And nothing was written

  Scenario: L'admin peut choisir une salle active ; sinon un type qui exige une salle reçoit la salle par défaut du praticien si libre, puis la première salle libre du département, sinon `no_room_available`. (salle choisie)
    When the admin books the patient at "2026-11-20 10:30" with "A" in room "R2"
    Then the appointment is "BOOKED" in room "R2"

  Scenario: L'admin peut choisir une salle active ; sinon un type qui exige une salle reçoit la salle par défaut du praticien si libre, puis la première salle libre du département, sinon `no_room_available`. (salle inactive ou d'un autre département)
    Given an inactive room "R3" in that department
    When the admin books the patient at "2026-11-20 10:30" with "A" in room "R3"
    Then the booking is refused as "not_found"
    And nothing was written

  Scenario Outline: L'admin peut choisir une salle active ; sinon un type qui exige une salle reçoit la salle par défaut du praticien si libre, puis la première salle libre du département, sinon `no_room_available`. (<case>)
    Given the rooms "<busy>" are used by someone else from "2026-11-20 10:30" to "2026-11-20 11:00"
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the appointment is "BOOKED" in room "<room>"

    Examples:
      | case                 | busy | room |
      | salle par défaut     | R2   | R1   |
      | première salle libre | R1   | R2   |

  Scenario: L'admin peut choisir une salle active ; sinon un type qui exige une salle reçoit la salle par défaut du praticien si libre, puis la première salle libre du département, sinon `no_room_available`. (aucune salle libre)
    Given the rooms "R1, R2" are used by someone else from "2026-11-20 10:30" to "2026-11-20 11:00"
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the booking is refused as "no_room_available"
    And nothing was written

  Scenario: Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou de la salle renvoient `conflict`. (hors créneau)
    When the admin books the patient at "2026-11-20 13:00" with "A"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "outside_availability"
    And nothing was written

  Scenario: Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou de la salle renvoient `conflict`. (praticien occupé)
    Given "A" has an active appointment from "2026-11-20 10:45" to "2026-11-20 11:15"
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the booking is refused as "conflict"
    And the refusal names the resources "clinician"

  Scenario: Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou de la salle renvoient `conflict`. (patient occupé)
    Given the patient has an active appointment with "B" from "2026-11-20 10:45" to "2026-11-20 11:15"
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the booking is refused as "conflict"
    And the refusal names the resources "patient"

  Scenario: Le début doit être un créneau libre (`outside_availability`) ; les chevauchements du praticien, du patient ou de la salle renvoient `conflict`. (salle occupée)
    Given the room "R2" is used by someone else from "2026-11-20 10:45" to "2026-11-20 11:15"
    When the admin books the patient at "2026-11-20 10:30" with "A" in room "R2"
    Then the booking is refused as "conflict"
    And the refusal names the resources "room"

  Scenario: Le délai de 120 minutes et la limite de 3 réservations en ligne ne s'appliquent pas.
    Given the patient has 3 open online bookings
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the appointment is "BOOKED" for "STAFF"

  Scenario: Le RDV est créé `BOOKED` avec la source `STAFF` ; le patient reçoit une notification « RDV réservé » et un email.
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the appointment is "BOOKED" for "STAFF"
    And the patient has one "RDV réservé" notification about the booking
    And a confirmation was queued

  Scenario: La réservation laisse une entrée d'audit sans donnée personnelle.
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the audit entry "booking.appointment_booked" has the admin as actor and holds only "appointment_type_id, clinician_id, email_domain, room_id, source"
