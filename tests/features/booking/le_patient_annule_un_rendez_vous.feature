Feature: Le patient annule un rendez-vous
  En tant que patient connecté, avec ou sans mot de passe
  Je veux annuler un de mes RDV à venir en donnant un motif
  Afin que le créneau soit libéré pour un autre patient

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And a signed-in patient
    And the patient has a "BOOKED" appointment with "A" at "2026-11-23 09:00" in room "R1"

  Scenario: L'annulation passe par une boîte de confirmation avec un motif obligatoire ; sans motif, `invalid_input`.
    When the patient cancels it without a reason
    Then the booking is refused as "invalid_input"
    And the refusal names the field "reason"
    And nothing was changed or notified

  Scenario: Règle §3.1 : le motif d'annulation tient en 500 caractères au plus
    When the patient cancels it giving a reason of 501 characters
    Then the booking is refused as "invalid_input"
    And the refusal names the field "reason"
    And nothing was changed or notified

  Scenario: Un RDV qui commence dans moins de 24 h est refusé en `rule_violation` avec `cancellation_window_closed` ; l'action « Annuler » n'est proposée que quand les règles la permettent. (moins de 24 h)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-21 09:00" in room "R1"
    When the patient cancels it giving the reason "Empêchement"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "cancellation_window_closed"
    And nothing was changed or notified

  Scenario Outline: Un RDV qui commence dans moins de 24 h est refusé en `rule_violation` avec `cancellation_window_closed` ; l'action « Annuler » n'est proposée que quand les règles la permettent. (<case>)
    Given the patient has a "<status>" appointment with "A" at "<start>" in room "R1"
    Then the patient is offered "<actions>"

    Examples:
      | case                          | status     | start            | actions            |
      | réservé dans plus de 24 h     | BOOKED     | 2026-11-23 09:00 | cancel, reschedule |
      | arrivé dans plus de 24 h      | CHECKED_IN | 2026-11-23 09:00 | cancel             |
      | réservé dans moins de 24 h    | BOOKED     | 2026-11-21 09:00 | nothing            |
      | terminé                       | COMPLETED  | 2026-11-23 09:00 | nothing            |

  Scenario Outline: Un RDV `COMPLETED`, `CANCELLED` ou `NO_SHOW` est refusé en `invalid_transition` avec son statut courant. (<case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-23 09:00" in room "R1"
    When the patient cancels it giving the reason "Empêchement"
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "<status>"
    And nothing was changed or notified

    Examples:
      | case         | status    |
      | terminé      | COMPLETED |
      | déjà annulé  | CANCELLED |
      | absent       | NO_SHOW   |

  Scenario Outline: Le RDV passe en `CANCELLED` avec la date et le motif de l'annulation, et rejoint les RDV passés. (<case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-23 09:00" in room "R1"
    When the patient cancels it giving the reason "  Empêchement professionnel  "
    Then the appointment is cancelled now for the reason "Empêchement professionnel"
    And the slots of "A" were refreshed
    And the appointment has left the upcoming appointments for the past ones

    Examples:
      | case    | status     |
      | réservé | BOOKED     |
      | arrivé  | CHECKED_IN |

  Scenario: La notification « RDV annulé » est créée dans la même transaction ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion. Une annulation refusée ne notifie rien. (annulation acceptée)
    When the patient cancels it giving the reason "Empêchement professionnel"
    Then the patient has one "RDV annulé" notification about the appointment
    And one email "Votre rendez-vous est annulé" names the time, hospital and provider, without the reason, linking only to the sign-in page

  Scenario: La notification « RDV annulé » est créée dans la même transaction ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion. Une annulation refusée ne notifie rien. (annulation refusée)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-21 09:00" in room "R1"
    When the patient cancels it giving the reason "Empêchement"
    Then nothing was changed or notified

  Scenario: L'annulation laisse une entrée d'audit sans le motif.
    When the patient cancels it giving the reason "Empêchement professionnel"
    Then the audit entry "booking.appointment_cancelled" has the patient as actor and holds no reason

  Scenario: Règle §12.3 : le RDV d'un autre patient est refusé en `forbidden`, un RDV inconnu en `not_found`
    Given the appointment belongs to another patient
    When the patient cancels it giving the reason "Empêchement"
    Then the booking is refused as "forbidden"
    And nothing was changed or notified
    When the patient cancels an unknown appointment
    Then the booking is refused as "not_found"
