Feature: Le praticien déplace un RDV
  En tant que praticien
  Je veux déplacer un de mes RDV depuis un bandeau de la semaine
  Afin que le patient soit vu à un autre moment sans nouvelle réservation

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2, R3" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And the signed-in clinician is "A"
    And the patient has a "BOOKED" appointment with "A" at "2026-11-20 11:00" in room "R2"
    And "A" is free at "2026-11-20 10:30"

  Scenario Outline: Seul un RDV `BOOKED` peut être déplacé ; sinon `invalid_transition` avec le statut courant. (<case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-20 11:00" in room "R2"
    When the clinician moves it to "2026-11-20 10:30"
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "<status>"
    And nothing was changed or notified

    Examples:
      | case    | status     |
      | arrivé  | CHECKED_IN |
      | terminé | COMPLETED  |
      | annulé  | CANCELLED  |
      | absent  | NO_SHOW    |

  Scenario: Le bandeau propose les créneaux libres du même praticien pour le même type ; le praticien et le type ne changent pas. (bandeau)
    Given "A" has a free slot in the week strip at "2026-11-20 10:30"
    Then the clinician's week strip of "A" offers "2026-11-20 10:30"
    And the patient's week strip of "A" does not offer "2026-11-20 10:30"

  Scenario: Le bandeau propose les créneaux libres du même praticien pour le même type ; le praticien et le type ne changent pas. (praticien et type gardés)
    When the clinician moves it to "2026-11-20 10:30"
    Then the appointment keeps its clinician "A" and its type

  Scenario: Un début qui n'est pas un créneau libre renvoie `rule_violation` avec `outside_availability` ; un chevauchement avec un RDV actif du patient ou de la salle renvoie `conflict`, le RDV déplacé étant ignoré. (hors créneau)
    When the clinician moves it to "2026-11-20 13:00"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "outside_availability"
    And nothing was changed or notified

  Scenario: Un début qui n'est pas un créneau libre renvoie `rule_violation` avec `outside_availability` ; un chevauchement avec un RDV actif du patient ou de la salle renvoie `conflict`, le RDV déplacé étant ignoré. (autre RDV du patient)
    Given the patient has an active appointment with "B" from "2026-11-20 10:15" to "2026-11-20 10:45"
    When the clinician moves it to "2026-11-20 10:30"
    Then the booking is refused as "conflict"
    And the refusal names the resources "patient"
    And nothing was changed or notified

  Scenario: Un début qui n'est pas un créneau libre renvoie `rule_violation` avec `outside_availability` ; un chevauchement avec un RDV actif du patient ou de la salle renvoie `conflict`, le RDV déplacé étant ignoré. (RDV déplacé ignoré)
    Given "A" is free at "2026-11-20 11:15" once the appointment is ignored
    When the clinician moves it to "2026-11-20 11:15"
    Then the appointment is "BOOKED" from "2026-11-20 11:15" for 30 minutes in room "R2"

  Scenario: Le délai de 120 minutes, la fenêtre de 24 heures et la réservabilité en ligne du type ne s'appliquent pas.
    Given the appointment type is not bookable online
    When the clinician moves it to "2026-11-20 10:30"
    Then the appointment is "BOOKED" from "2026-11-20 10:30" for 30 minutes in room "R2"

  Scenario Outline: La salle est réattribuée en préférant la salle courante ; aucune salle libre donne `no_room_available`. (<case>)
    Given the rooms "<busy>" are used by someone else from "2026-11-20 10:30" to "2026-11-20 11:00"
    When the clinician moves it to "2026-11-20 10:30"
    Then the appointment is "BOOKED" from "2026-11-20 10:30" for 30 minutes in room "<room>"

    Examples:
      | case                 | busy | room |
      | salle courante libre | R1   | R2   |
      | salle courante prise | R2   | R1   |

  Scenario: La salle est réattribuée en préférant la salle courante ; aucune salle libre donne `no_room_available`. (aucune salle libre)
    Given the rooms "R1, R2, R3" are used by someone else from "2026-11-20 10:30" to "2026-11-20 11:00"
    When the clinician moves it to "2026-11-20 10:30"
    Then the booking is refused as "no_room_available"
    And nothing was changed or notified

  Scenario: Le patient reçoit une notification « RDV déplacé » et un email.
    When the clinician moves it to "2026-11-20 10:30"
    Then the patient has one "RDV déplacé" notification about the appointment
    And one email "Votre rendez-vous est déplacé" names the time, hospital and provider, without the reason, linking only to the sign-in page

  Scenario: Sur le RDV d'un autre praticien, le déplacement est refusé avec `forbidden`.
    Given the signed-in clinician is "B"
    When the clinician moves it to "2026-11-20 10:30"
    Then the booking is refused as "forbidden"
    And nothing was changed or notified

  Scenario: Le déplacement laisse une entrée d'audit sans donnée personnelle.
    When the clinician moves it to "2026-11-20 10:30"
    Then the audit entry "booking.appointment_rescheduled" has the clinician as actor and holds only "clinician_id, room_id"

  Scenario: Le déplacement est aussi disponible par `POST /appointments/{id}/reschedule` (§14). (déplacement accepté)
    When the clinician posts '{"start": "2026-11-20T10:30:00Z"}' to reschedule it
    Then the API answers 200 with the appointment "BOOKED"
    And the appointment is "BOOKED" from "2026-11-20 10:30" for 30 minutes in room "R2"

  Scenario: Le déplacement est aussi disponible par `POST /appointments/{id}/reschedule` (§14). (hors créneau)
    When the clinician posts '{"start": "2026-11-20T13:00:00Z"}' to reschedule it
    Then the API refuses with 422 "rule_violation"
    And the API refusal names the rules "outside_availability"
    And nothing was changed or notified
