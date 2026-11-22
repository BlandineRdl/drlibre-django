Feature: L'admin consulte le journal d'audit en FHIR
  En tant que client API agissant pour un admin
  Je veux rechercher les entrées du journal d'audit en `AuditEvent`
  Afin qu'un outil externe exploite la traçabilité du produit

  Background:
    Given a bookable department with two clinicians, one room, two patients and an admin
    And "first" has booked "clinician" at "09:00"
    And "first" has signed in on the application API

  Scenario: Chaque entrée d'audit est un `AuditEvent` avec action, heure, agent, entité, métadonnées en détails d'entité et correlation id ; les connexions y figurent.
    When "admin" searches the audit events with "agent=Patient/$first"
    Then the audit actions found are "booking.appointment_booked, auth.login_succeeded"
    And each audit event of "first" carries its entry's action, time, actor, entity, metadata and correlation id
    And the sign-in event names "Patient/$first" and the correlation id of the sign-in
    And the booking event names the appointment of "first"
    And no audit event shows a name or an email beyond the audited metadata

  Scenario Outline: Seul l'admin lit et recherche les `AuditEvent` ; tout autre utilisateur reçoit `forbidden`. (<case>)
    When "<who>" reads the sign-in event of "first"
    Then the client is answered <answer>
    When "<who>" searches the audit events with ""
    Then the client is answered <answer>

    Examples:
      | case         | who       | answer |
      | l'admin      | admin     | 200    |
      | un patient   | first     | 403    |
      | un praticien | clinician | 403    |

  Scenario Outline: Les recherches acceptent `agent`, `entity`, `entity-type`, `action` et `date`. (<case>)
    When "admin" searches the audit events with "agent=Patient/$first&<query>"
    Then the audit actions found are "<found>"

    Examples:
      | case        | query                       | found                                            |
      | agent       | _sort=-date                 | auth.login_succeeded, booking.appointment_booked |
      | entity      | entity=Patient/$first       | auth.login_succeeded                             |
      | entity-type | entity-type=appointment     | booking.appointment_booked                       |
      | action      | action=E                    | booking.appointment_booked, auth.login_succeeded |
      | action C    | action=C,U,D                |                                                  |
      | date        | date=lt2026-11-20           |                                                  |

  Scenario Outline: Aucune création, modification ni suppression d'`AuditEvent` n'est acceptée. (<case>)
    When "admin" sends "<method>" to the audit event of "first"
    Then the client is refused with 405 as not supported

    Examples:
      | case         | method |
      | création     | POST   |
      | modification | PUT    |
      | suppression  | DELETE |
