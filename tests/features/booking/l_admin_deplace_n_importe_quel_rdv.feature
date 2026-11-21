Feature: L'admin déplace n'importe quel RDV
  En tant qu'admin
  Je veux déplacer un RDV de n'importe quel praticien
  Afin que je règle un changement de planning pour le patient

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2, R3" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And a signed-in admin
    And the patient has a "BOOKED" appointment with "A" at "2026-11-20 11:00" in room "R2"
    And "A" is free at "2026-11-20 10:30"

  Scenario Outline: Seul un RDV `BOOKED` peut être déplacé ; sinon `invalid_transition` avec le statut courant. (<case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-20 11:00" in room "R2"
    When the admin moves it to "2026-11-20 10:30"
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "<status>"
    And nothing was changed or notified

    Examples:
      | case    | status     |
      | arrivé  | CHECKED_IN |
      | terminé | COMPLETED  |

  Scenario: Le praticien et le type restent ceux du RDV ; le nouveau début doit être un de leurs créneaux libres (`outside_availability`). (praticien et type gardés)
    When the admin moves it to "2026-11-20 10:30"
    Then the appointment keeps its clinician "A" and its type

  Scenario: Le praticien et le type restent ceux du RDV ; le nouveau début doit être un de leurs créneaux libres (`outside_availability`). (hors créneau)
    When the admin moves it to "2026-11-20 13:00"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "outside_availability"
    And nothing was changed or notified

  Scenario: Un chevauchement avec un RDV actif du patient ou de la salle renvoie `conflict`, le RDV déplacé étant ignoré ; les règles réservées aux patients ne s'appliquent pas. (autre RDV du patient)
    Given the patient has an active appointment with "B" from "2026-11-20 10:15" to "2026-11-20 10:45"
    When the admin moves it to "2026-11-20 10:30"
    Then the booking is refused as "conflict"
    And the refusal names the resources "patient"
    And nothing was changed or notified

  Scenario: Un chevauchement avec un RDV actif du patient ou de la salle renvoie `conflict`, le RDV déplacé étant ignoré ; les règles réservées aux patients ne s'appliquent pas. (RDV déplacé ignoré)
    Given "A" is free at "2026-11-20 11:15" once the appointment is ignored
    When the admin moves it to "2026-11-20 11:15"
    Then the appointment is "BOOKED" from "2026-11-20 11:15" for 30 minutes in room "R2"

  Scenario: Un chevauchement avec un RDV actif du patient ou de la salle renvoie `conflict`, le RDV déplacé étant ignoré ; les règles réservées aux patients ne s'appliquent pas. (règles des patients)
    Given the appointment type is not bookable online
    When the admin moves it to "2026-11-20 10:30"
    Then the appointment is "BOOKED" from "2026-11-20 10:30" for 30 minutes in room "R2"

  Scenario Outline: La salle est réattribuée en préférant la salle courante ; aucune salle libre donne `no_room_available`. (<case>)
    Given the rooms "<busy>" are used by someone else from "2026-11-20 10:30" to "2026-11-20 11:00"
    When the admin moves it to "2026-11-20 10:30"
    Then the appointment is "BOOKED" from "2026-11-20 10:30" for 30 minutes in room "<room>"

    Examples:
      | case                 | busy | room |
      | salle courante libre | R1   | R2   |
      | salle courante prise | R2   | R1   |

  Scenario: La salle est réattribuée en préférant la salle courante ; aucune salle libre donne `no_room_available`. (aucune salle libre)
    Given the rooms "R1, R2, R3" are used by someone else from "2026-11-20 10:30" to "2026-11-20 11:00"
    When the admin moves it to "2026-11-20 10:30"
    Then the booking is refused as "no_room_available"
    And nothing was changed or notified

  Scenario: Le patient reçoit une notification « RDV déplacé » et un email.
    When the admin moves it to "2026-11-20 10:30"
    Then the patient has one "RDV déplacé" notification about the appointment
    And one email "Votre rendez-vous est déplacé" names the time, hospital and provider, without the reason, linking only to the sign-in page

  Scenario: Le déplacement est aussi disponible par `POST /appointments/{id}/reschedule` (§14).
    When the admin posts '{"start": "2026-11-20T10:30:00Z"}' to reschedule it
    Then the API answers 200 with the appointment "BOOKED"
    And the appointment is "BOOKED" from "2026-11-20 10:30" for 30 minutes in room "R2"

  Scenario: Le déplacement laisse une entrée d'audit sans donnée personnelle.
    When the admin moves it to "2026-11-20 10:30"
    Then the audit entry "booking.appointment_rescheduled" has the admin as actor and holds only "clinician_id, room_id"
