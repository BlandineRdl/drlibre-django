Feature: L'admin accepte une offre pour un patient
  En tant qu'admin
  Je veux accepter l'offre d'une entrée pour son patient
  Afin que le patient obtienne le RDV sans agir lui-même

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And a signed-in admin

  Scenario: L'admin accepte une entrée `OFFERED` de n'importe quel patient : RDV `BOOKED` placé avec le praticien, le type et le début offerts, source `STAFF` ; l'entrée passe en `BOOKED`.
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    When the admin accepts the offer of "patient@example.org"
    Then the appointment is "BOOKED" for "STAFF"
    And the appointment of "patient@example.org" is with "A" at "2026-11-23 09:00" for the offered type
    And the entry of "patient@example.org" is now "BOOKED"

  Scenario Outline: Seules les règles du personnel s'appliquent : créneau libre exact et absence de conflit. (<case>)
    Given "patient@example.org" is offered the cancelled appointment with "A" at "<start>"
    And "A" is free at "<start>"
    And <condition>
    When the admin accepts the offer of "patient@example.org"
    Then the appointment is "BOOKED" for "STAFF"
    And the entry of "patient@example.org" is now "BOOKED"

    Examples:
      | case                              | start            | condition                                 |
      | début sous 120 min                | 2026-11-20 11:00 | the appointment type is bookable online   |
      | 3 réservations en ligne ouvertes  | 2026-11-23 09:00 | the patient has 3 open online bookings    |
      | type non réservable en ligne      | 2026-11-23 09:00 | the appointment type is not bookable online |

  Scenario: Seules les règles du personnel s'appliquent : créneau libre exact et absence de conflit. (créneau plus libre)
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    When the admin accepts the offer of "patient@example.org"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "outside_availability"
    And the entry of "patient@example.org" is unchanged
    And nothing was written

  Scenario: Si le créneau a été pris entre-temps, l'acceptation échoue en `conflict` avec les ressources en cause et l'entrée repasse en `WAITING`.
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    And the patient has an active appointment with "B" from "2026-11-23 09:00" to "2026-11-23 09:30"
    When the admin accepts the offer of "patient@example.org"
    Then the booking is refused as "conflict"
    And the refusal names the resources "patient"
    And the entry of "patient@example.org" is now "WAITING" with no offer
    And the audit holds "booking.waitlist_offer_lost" by the admin with ids only
    And nothing was written

  Scenario: La notification « Créneau réservé » ne porte que l'heure ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion.
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    When the admin accepts the offer of "patient@example.org"
    Then "patient@example.org" has one "Créneau réservé" notification at "23/11/2026 à 10:00" about the appointment
    And one email "Votre créneau est réservé" to "patient@example.org" names the time "2026-11-23 09:00", hospital and provider "A", without a reason, linking only to the sign-in page

  Scenario: L'acceptation laisse une entrée d'audit dont l'acteur est l'admin, sans donnée personnelle.
    Given "patient@example.org" is offered the cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    When the admin accepts the offer of "patient@example.org"
    Then the audit holds "booking.waitlist_accepted" by the admin, with ids and the source only
