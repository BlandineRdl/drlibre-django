Feature: Le patient accepte un créneau proposé
  En tant que patient connecté, avec ou sans mot de passe
  Je veux accepter le créneau qu'on me propose
  Afin qu'il devienne mon RDV

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient

  Scenario: Accepter une de ses entrées `OFFERED` place un RDV avec le praticien, le type et le début offerts : RDV `BOOKED`, source `ONLINE` ; l'entrée passe en `BOOKED`.
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    When the patient accepts the offer of "patient@example.org"
    Then the appointment is "BOOKED" for "ONLINE"
    And the appointment of "patient@example.org" is with "A" at "2026-11-23 09:00" for the offered type
    And the entry of "patient@example.org" is now "BOOKED"

  Scenario: Les règles patient s'appliquent : début à au moins 120 min, moins de 3 réservations en ligne ouvertes, type réservable en ligne, créneau libre exact ; sinon `rule_violation` avec les règles violées. (début trop proche)
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-20 11:00"
    And "A" is free at "2026-11-20 11:00"
    When the patient accepts the offer of "patient@example.org"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "lead_time_too_short"
    And the entry of "patient@example.org" is unchanged
    And nothing was written

  Scenario: Les règles patient s'appliquent : début à au moins 120 min, moins de 3 réservations en ligne ouvertes, type réservable en ligne, créneau libre exact ; sinon `rule_violation` avec les règles violées. (3 réservations en ligne ouvertes)
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    And the patient has 3 open online bookings
    When the patient accepts the offer of "patient@example.org"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "too_many_open_bookings"
    And the entry of "patient@example.org" is unchanged
    And nothing was written

  Scenario: Les règles patient s'appliquent : début à au moins 120 min, moins de 3 réservations en ligne ouvertes, type réservable en ligne, créneau libre exact ; sinon `rule_violation` avec les règles violées. (type non réservable en ligne)
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    And the appointment type is not bookable online
    When the patient accepts the offer of "patient@example.org"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "type_not_bookable_online"
    And the entry of "patient@example.org" is unchanged
    And nothing was written

  Scenario: Les règles patient s'appliquent : début à au moins 120 min, moins de 3 réservations en ligne ouvertes, type réservable en ligne, créneau libre exact ; sinon `rule_violation` avec les règles violées. (créneau plus libre)
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    When the patient accepts the offer of "patient@example.org"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "outside_availability"
    And the entry of "patient@example.org" is unchanged
    And nothing was written

  Scenario: Si le créneau a été pris entre-temps, l'acceptation échoue en `conflict` avec les ressources en cause et l'entrée repasse en `WAITING`.
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    And "A" has an active appointment from "2026-11-23 09:00" to "2026-11-23 09:30"
    When the patient accepts the offer of "patient@example.org"
    Then the booking is refused as "conflict"
    And the refusal names the resources "clinician"
    And the entry of "patient@example.org" is now "WAITING" with no offer
    And the audit holds "booking.waitlist_offer_lost" by the signed-in patient with ids only
    And nothing was written

  Scenario: La notification « Créneau réservé » ne porte que l'heure ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion.
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    When the patient accepts the offer of "patient@example.org"
    Then "patient@example.org" has one "Créneau réservé" notification at "23/11/2026 à 10:00" about the appointment
    And one email "Votre créneau est réservé" to "patient@example.org" names the time "2026-11-23 09:00", hospital and provider "A", without a reason, linking only to the sign-in page

  Scenario: L'acceptation laisse une entrée d'audit sans donnée personnelle.
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    When the patient accepts the offer of "patient@example.org"
    Then the audit holds "booking.waitlist_accepted" by the signed-in patient, with ids and the source only

  Scenario: Règle §5.8 : seule une entrée proposée s'accepte
    Given "patient@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    When the patient accepts the offer of "patient@example.org"
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "WAITING"
    And nothing was written

  Scenario: Règle §5.8 : un patient n'accepte que ses propres entrées
    Given an active patient "lea@example.org"
    And "lea@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    When the patient accepts the offer of "lea@example.org"
    Then the booking is refused as "forbidden"
    And the entry of "lea@example.org" is unchanged
    And nothing was written

  Scenario: Règle §5.8 : un praticien ne peut pas accepter une offre
    Given an active patient "lea@example.org"
    And "lea@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    And a signed-in clinician
    When the clinician accepts the offer of "lea@example.org"
    Then the booking is refused as "forbidden"
    And the entry of "lea@example.org" is unchanged
    And nothing was written

  Scenario: Règle §5.8 : une entrée inconnue est introuvable
    When the patient accepts an unknown entry
    Then the booking is refused as "not_found"
    And nothing was written

  Scenario: `POST /waitlist/{id}/accept` applique les mêmes règles, sur les seules entrées du patient ; un praticien reçoit `forbidden`. (ses entrées)
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    When the patient posts the acceptance of the offer of "patient@example.org"
    Then the appointment is "BOOKED" for "ONLINE"
    And the entry of "patient@example.org" is now "BOOKED"

  Scenario: `POST /waitlist/{id}/accept` applique les mêmes règles, sur les seules entrées du patient ; un praticien reçoit `forbidden`. (entrée non proposée)
    Given "patient@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    When the patient posts the acceptance of the offer of "patient@example.org"
    Then the API refuses with 409 "invalid_transition"
    And nothing was written

  Scenario: `POST /waitlist/{id}/accept` applique les mêmes règles, sur les seules entrées du patient ; un praticien reçoit `forbidden`. (entrée d'un autre)
    Given an active patient "lea@example.org"
    And "lea@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    When the patient posts the acceptance of the offer of "lea@example.org"
    Then the API refuses with 403 "forbidden"
    And the entry of "lea@example.org" is unchanged

  Scenario: `POST /waitlist/{id}/accept` applique les mêmes règles, sur les seules entrées du patient ; un praticien reçoit `forbidden`. (praticien)
    Given an active patient "lea@example.org"
    And "lea@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    And a signed-in clinician
    When the clinician posts the acceptance of the offer of "lea@example.org"
    Then the API refuses with 403 "forbidden"
    And the entry of "lea@example.org" is unchanged
