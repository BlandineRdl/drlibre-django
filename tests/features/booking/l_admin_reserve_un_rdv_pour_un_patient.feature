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

  Scenario Outline: L'admin choisit le patient par son nom ou son email, parmi les patients actifs. (<case>)
    Given these people
      | name        | email               | role      | active |
      | Zoé Martin  | zoe@martin.example  | PATIENT   | yes    |
      | Paul Martin | paul@martin.example | PATIENT   | no     |
      | Léa Martin  | lea@martin.example  | CLINICIAN | yes    |
    When the admin looks for the patients matching "<text>"
    Then the patients found are "Zoé Martin"

    Examples:
      | case     | text            |
      | nom      | MARTIN          |
      | email    | @martin.example |

  Scenario: L'assistant enchaîne type, praticien et créneau ; il ne propose pas « premier disponible » et inclut les types non réservables en ligne. (type non réservable en ligne)
    Given the appointment type is not bookable online
    When the admin books the patient at "2026-11-20 10:30" with "A"
    Then the appointment is with "A"
    And the appointment is of that type from "2026-11-20 10:30" for 30 minutes
    And the appointment belongs to the signed-in patient

  Scenario: La même réservation est disponible par `POST /appointments`, qui exige un praticien pour l'admin (§14). (praticien nommé)
    When the admin posts the booking of the patient at "2026-11-20T10:30:00Z" with "A"
    Then the API answers 201 with an appointment with "A"
    And the appointment is "BOOKED" for "STAFF"

  Scenario: La même réservation est disponible par `POST /appointments`, qui exige un praticien pour l'admin (§14). (sans praticien)
    When the admin posts the booking of the patient at "2026-11-20T10:30:00Z" without a clinician
    Then the API refuses with 400 "invalid_input"
    And the API refusal names the field "clinician"
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

  Scenario: Règle §5.2 : une salle nommée est vérifiée avant les conflits et les règles de réservation
    Given an inactive room "R3" in that department
    When the admin books the patient at "2026-11-20 13:00" with "A" in room "R3"
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
