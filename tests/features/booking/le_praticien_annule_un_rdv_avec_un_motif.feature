Feature: Le praticien annule un RDV avec un motif
  En tant que praticien
  Je veux annuler un de mes RDV en donnant un motif
  Afin que le patient soit prévenu et le créneau libéré

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And the signed-in clinician is "A"
    And the patient has a "BOOKED" appointment with "A" at "2026-11-20 12:00" in room "R1"

  Scenario Outline: L'annulation est possible depuis `BOOKED` ou `CHECKED_IN` ; depuis un autre statut, elle renvoie `invalid_transition` avec le statut courant. (<case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-20 12:00" in room "R1"
    When the clinician cancels it giving the reason "Urgence au bloc"
    Then the appointment is cancelled now for the reason "Urgence au bloc"
    And the slots of "A" were refreshed

    Examples:
      | case    | status     |
      | réservé | BOOKED     |
      | arrivé  | CHECKED_IN |

  Scenario Outline: L'annulation est possible depuis `BOOKED` ou `CHECKED_IN` ; depuis un autre statut, elle renvoie `invalid_transition` avec le statut courant. (refusée : <case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-20 12:00" in room "R1"
    When the clinician cancels it giving the reason "Urgence au bloc"
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "<status>"
    And nothing was changed or notified

    Examples:
      | case    | status    |
      | terminé | COMPLETED |
      | annulé  | CANCELLED |
      | absent  | NO_SHOW   |

  Scenario: Le motif est obligatoire ; sans motif, `invalid_input`.
    When the clinician cancels it giving the reason "   "
    Then the booking is refused as "invalid_input"
    And the refusal names the field "reason"
    And nothing was changed or notified

  Scenario: La règle des 24 heures des patients ne s'applique pas au praticien.
    When the clinician cancels it giving the reason "Urgence au bloc"
    Then the appointment is now "CANCELLED"

  Scenario: La règle des 24 heures des patients ne s'applique pas au praticien. (le patient y reste soumis)
    When the patient cancels it giving the reason "Empêchement"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "cancellation_window_closed"

  Scenario: L'heure et le motif d'annulation sont enregistrés sur le RDV.
    When the clinician cancels it giving the reason "  Urgence au bloc  "
    Then the appointment is cancelled now for the reason "Urgence au bloc"

  Scenario: Le patient reçoit une notification « RDV annulé », sans nom ni motif, et un email.
    When the clinician cancels it giving the reason "Urgence au bloc"
    Then the patient has one "RDV annulé" notification about the appointment
    And the notification names neither the patient nor the reason
    And one email "Votre rendez-vous est annulé" names the time, hospital and provider, without the reason, linking only to the sign-in page

  Scenario: Sur le RDV d'un autre praticien, l'annulation est refusée avec `forbidden`.
    Given the signed-in clinician is "B"
    When the clinician cancels it giving the reason "Urgence au bloc"
    Then the booking is refused as "forbidden"
    And nothing was changed or notified

  Scenario: L'annulation laisse une entrée d'audit sans le motif ni donnée personnelle.
    When the clinician cancels it giving the reason "Urgence au bloc"
    Then the audit entry "booking.appointment_cancelled" has the clinician as actor and holds only "clinician_id"

  Scenario: L'annulation est aussi disponible par `POST /appointments/{id}/cancel` (§14). (annulation acceptée)
    When the clinician posts '{"reason": "Urgence au bloc"}' to cancel it
    Then the API answers 200 with the appointment "CANCELLED"
    And the appointment is cancelled now for the reason "Urgence au bloc"

  Scenario: L'annulation est aussi disponible par `POST /appointments/{id}/cancel` (§14). (sans motif)
    When the clinician posts '{"reason": "   "}' to cancel it
    Then the API refuses with 400 "invalid_input"
    And the API refusal names the field "reason"
    And nothing was changed or notified
