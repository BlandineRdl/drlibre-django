Feature: L'admin annule ou change le statut de n'importe quel RDV
  En tant qu'admin
  Je veux marquer arrivé, terminé, absent ou annuler n'importe quel RDV
  Afin que je corrige l'activité de tout hôpital

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And a signed-in patient
    And a signed-in admin

  Scenario Outline: Les transitions sont celles du personnel : `BOOKED` vers `CHECKED_IN`, `NO_SHOW` ou `CANCELLED` ; `CHECKED_IN` vers `COMPLETED` ou `CANCELLED` ; une autre renvoie `invalid_transition` avec le statut courant. (<case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the admin applies "<action>" to it
    Then the appointment is now "<to>"

    Examples:
      | case                | from       | action   | to         |
      | réservé puis arrivé | BOOKED     | check_in | CHECKED_IN |
      | réservé puis absent | BOOKED     | no_show  | NO_SHOW    |
      | arrivé puis terminé | CHECKED_IN | complete | COMPLETED  |

  Scenario Outline: Les transitions sont celles du personnel : `BOOKED` vers `CHECKED_IN`, `NO_SHOW` ou `CANCELLED` ; `CHECKED_IN` vers `COMPLETED` ou `CANCELLED` ; une autre renvoie `invalid_transition` avec le statut courant. (annulation depuis <case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the admin cancels it giving the reason "Erreur de planning"
    Then the appointment is cancelled now for the reason "Erreur de planning"

    Examples:
      | case    | from       |
      | réservé | BOOKED     |
      | arrivé  | CHECKED_IN |

  Scenario Outline: Les transitions sont celles du personnel : `BOOKED` vers `CHECKED_IN`, `NO_SHOW` ou `CANCELLED` ; `CHECKED_IN` vers `COMPLETED` ou `CANCELLED` ; une autre renvoie `invalid_transition` avec le statut courant. (refusée : <case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the admin applies "<action>" to it
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "<from>"
    And nothing was changed or notified

    Examples:
      | case                     | from       | action   |
      | terminé puis arrivé      | COMPLETED  | check_in |
      | réservé terminé d'emblée | BOOKED     | complete |
      | arrivé marqué absent     | CHECKED_IN | no_show  |

  Scenario: Les transitions sont celles du personnel : `BOOKED` vers `CHECKED_IN`, `NO_SHOW` ou `CANCELLED` ; `CHECKED_IN` vers `COMPLETED` ou `CANCELLED` ; une autre renvoie `invalid_transition` avec le statut courant. (annulation d'un RDV terminé)
    Given the patient has a "COMPLETED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the admin cancels it giving the reason "Erreur de planning"
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "COMPLETED"
    And nothing was changed or notified

  Scenario Outline: Arrivée, terminé et absent ne notifient pas le patient. (<case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the admin applies "<action>" to it
    Then the appointment is now "<to>"
    And no one was notified

    Examples:
      | case    | from       | action   | to         |
      | arrivé  | BOOKED     | check_in | CHECKED_IN |
      | absent  | BOOKED     | no_show  | NO_SHOW    |
      | terminé | CHECKED_IN | complete | COMPLETED  |

  Scenario: L'annulation exige un motif, ignore la règle des 24 heures, enregistre l'heure et le motif, notifie le patient (« RDV annulé ») et lui envoie un email, puis lance l'offre automatique de la liste d'attente. (sans motif)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 12:00" in room "R1"
    When the admin cancels it giving the reason "   "
    Then the booking is refused as "invalid_input"
    And the refusal names the field "reason"
    And nothing was changed or notified

  Scenario: L'annulation exige un motif, ignore la règle des 24 heures, enregistre l'heure et le motif, notifie le patient (« RDV annulé ») et lui envoie un email, puis lance l'offre automatique de la liste d'attente. (dans les 24 heures)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 12:00" in room "R1"
    When the admin cancels it giving the reason "  Erreur de planning  "
    Then the appointment is cancelled now for the reason "Erreur de planning"
    And the slots of "A" were refreshed

  Scenario: L'annulation exige un motif, ignore la règle des 24 heures, enregistre l'heure et le motif, notifie le patient (« RDV annulé ») et lui envoie un email, puis lance l'offre automatique de la liste d'attente. (patient prévenu)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 12:00" in room "R1"
    When the admin cancels it giving the reason "Erreur de planning"
    Then the patient has one "RDV annulé" notification about the appointment
    And the notification names neither the patient nor the reason
    And one email "Votre rendez-vous est annulé" names the time, hospital and provider, without the reason, linking only to the sign-in page

  Scenario: L'annulation exige un motif, ignore la règle des 24 heures, enregistre l'heure et le motif, notifie le patient (« RDV annulé ») et lui envoie un email, puis lance l'offre automatique de la liste d'attente. (offre de la liste d'attente)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 12:00" in room "R1"
    And an active patient "lea@example.org"
    And "lea@example.org" waits from "2026-11-20 00:00" to "2026-11-21 00:00" since "2026-11-01 08:00"
    When the admin cancels it giving the reason "Erreur de planning"
    Then the entry of "lea@example.org" is offered the appointment the patient cancelled

  Scenario Outline: Les mêmes actions sont disponibles par `POST /appointments/{id}/check-in`, `/complete`, `/no-show` et `/cancel` (§14). (<case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the admin posts '<body>' to <path> it
    Then the API answers 200 with the appointment "<to>"
    And the appointment is now "<to>"

    Examples:
      | case    | from       | path     | body                               | to         |
      | arrivé  | BOOKED     | check-in | {}                                 | CHECKED_IN |
      | absent  | BOOKED     | no-show  | {}                                 | NO_SHOW    |
      | terminé | CHECKED_IN | complete | {}                                 | COMPLETED  |
      | annulé  | BOOKED     | cancel   | {"reason": "Erreur de planning"}   | CANCELLED  |

  Scenario Outline: Chaque action laisse une entrée d'audit sans motif ni donnée personnelle. (<case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the admin applies "<action>" to it
    Then the audit records the change from "<from>" to "<to>" by the admin, with no personal data

    Examples:
      | case    | from       | action   | to         |
      | arrivé  | BOOKED     | check_in | CHECKED_IN |
      | absent  | BOOKED     | no_show  | NO_SHOW    |
      | terminé | CHECKED_IN | complete | COMPLETED  |

  Scenario: Chaque action laisse une entrée d'audit sans motif ni donnée personnelle. (annulation)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the admin cancels it giving the reason "Erreur de planning"
    Then the audit entry "booking.appointment_cancelled" has the admin as actor and holds only "clinician_id"

  Scenario: Règle §4 : un RDV inconnu est introuvable pour l'admin
    When the admin applies "check_in" to an unknown appointment
    Then the booking is refused as "not_found"

  Scenario: Règle §3.1 : les notes cliniques restent au praticien, l'admin est refusé
    Given the patient has a "CHECKED_IN" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the admin writes the notes "Tension normale"
    Then the booking is refused as "forbidden"
    And nothing was changed or notified

  Scenario: Règle §3.1 : l'admin ouvre la fiche de n'importe quel RDV, sans les notes cliniques
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And the appointment holds the notes "Tension normale"
    When the admin opens the appointment
    Then the file shows no notes and offers "check_in, no_show, cancel, reschedule"
