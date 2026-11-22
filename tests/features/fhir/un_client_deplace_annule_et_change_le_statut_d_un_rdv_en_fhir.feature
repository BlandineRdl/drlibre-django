Feature: Un client déplace, annule et change le statut d'un RDV en FHIR
  En tant que client API agissant pour un patient, un praticien ou un admin
  Je veux mettre à jour un `Appointment` pour le déplacer, l'annuler ou faire avancer son statut
  Afin que mon application suive le RDV jusqu'à sa clôture

  Background:
    Given a bookable department with two clinicians, one room, two patients and an admin
    And "first" has booked "clinician" at "09:00"
    And "second" has booked "clinician" at "10:00"

  Scenario: Mettre à jour le début déplace le RDV avec les règles du §5.6 : RDV `booked` seulement, même praticien et même type, règles patient pour un patient, salle réattribuée en préférant la courante. (déplacé comme par l'API)
    When "first" updates in FHIR the appointment of "first" with "start=11:00"
    Then the update answers "booked" at "11:00" with "clinician" and the room
    When "second" sends "start=11:30" to the application API for the appointment of "second"
    Then the "first" and "second" bookings leave alike audit entries, the same notification and the same email

  Scenario Outline: Mettre à jour le début déplace le RDV avec les règles du §5.6 : RDV `booked` seulement, même praticien et même type, règles patient pour un patient, salle réattribuée en préférant la courante. (refus : <case>)
    Given the appointment of "first" is "<status>"
    And the clock is at "<clock>"
    When "first" updates in FHIR the appointment of "first" with "start=11:00"
    Then the client is refused with <answer> and the code "<code>"
    And the application API answers the same to the same update

    Examples:
      | case                         | status     | clock                | answer | code               |
      | RDV déjà arrivé              | CHECKED_IN | 2026-11-20T10:00:00Z | 409    | invalid_transition |
      | moins de 24 heures à l'avance | BOOKED     | 2026-11-22T12:00:00Z | 422    | rule_violation     |

  Scenario Outline: Mettre à jour le début déplace le RDV avec les règles du §5.6 : RDV `booked` seulement, même praticien et même type, règles patient pour un patient, salle réattribuée en préférant la courante. (refus sans écriture : <case>)
    When "<who>" updates in FHIR the appointment of "first" with "<changes>"
    Then the client is refused with 400 and the code "invalid_input"
    And the refusal names the fields "<paths>"
    And the appointment of "first" is still "BOOKED" at "09:00"

    Examples:
      | case              | who   | changes                                           | paths                                                                   |
      | autre praticien   | admin | start=11:00, practitioner=colleague               | Appointment.participant                                                 |
      | autre type        | admin | start=11:00, type=absent                          | Appointment.serviceType                                                 |
      | déplacé et annulé | first | start=11:00, status=cancelled, reason=Empêchement | Appointment.cancelationReason, Appointment.start, Appointment.status |

  Scenario: Passer le statut à `cancelled` avec un `cancelationReason` annule le RDV ; sans motif, `invalid_input` ; un patient reste soumis à la fenêtre de 24 heures ; l'offre automatique de la liste d'attente est lancée. (annulé comme par l'API)
    When "first" updates in FHIR the appointment of "first" with "status=cancelled, reason=Empêchement"
    Then the update answers "cancelled" with the cancellation reason "Empêchement"
    When "second" sends "status=cancelled, reason=Empêchement" to the application API for the appointment of "second"
    Then the "first" and "second" bookings leave alike audit entries, the same notification and the same email

  Scenario: Passer le statut à `cancelled` avec un `cancelationReason` annule le RDV ; sans motif, `invalid_input` ; un patient reste soumis à la fenêtre de 24 heures ; l'offre automatique de la liste d'attente est lancée. (offre à la liste d'attente)
    Given "second" waits for a slot on Monday
    When "first" updates in FHIR the appointment of "first" with "status=cancelled, reason=Empêchement"
    Then the update answers "cancelled" with the cancellation reason "Empêchement"
    And the waitlist entry of "second" is offered the appointment of "first"

  Scenario Outline: Passer le statut à `cancelled` avec un `cancelationReason` annule le RDV ; sans motif, `invalid_input` ; un patient reste soumis à la fenêtre de 24 heures ; l'offre automatique de la liste d'attente est lancée. (refus : <case>)
    Given the clock is at "<clock>"
    When "<who>" updates in FHIR the appointment of "first" with "<changes>"
    Then the client is refused with <answer> and the code "<code>"
    And the application API answers the same to the same update
    And the appointment of "first" is still "BOOKED" at "09:00"

    Examples:
      | case                                 | who   | clock                | changes                               | answer | code           |
      | sans motif                           | first | 2026-11-20T10:00:00Z | status=cancelled                      | 400    | invalid_input  |
      | patient à moins de 24 heures         | first | 2026-11-22T12:00:00Z | status=cancelled, reason=Empêchement  | 422    | rule_violation |

  Scenario: Passer le statut à `cancelled` avec un `cancelationReason` annule le RDV ; sans motif, `invalid_input` ; un patient reste soumis à la fenêtre de 24 heures ; l'offre automatique de la liste d'attente est lancée. (praticien à moins de 24 heures)
    Given the clock is at "2026-11-22T12:00:00Z"
    When "clinician" updates in FHIR the appointment of "first" with "status=cancelled, reason=Empêchement"
    Then the update answers "cancelled" with the cancellation reason "Empêchement"

  Scenario: Passer le statut à `checked-in`, `fulfilled` ou `noshow` est réservé au praticien du RDV et à l'admin. (arrivée puis fin, comme par l'API)
    When "clinician" updates in FHIR the appointment of "first" with "status=checked-in"
    Then the update answers "checked-in"
    When "clinician" updates in FHIR the appointment of "first" with "status=fulfilled"
    Then the update answers "fulfilled"
    When "clinician" sends "status=checked-in" to the application API for the appointment of "second"
    And "clinician" sends "status=fulfilled" to the application API for the appointment of "second"
    Then the "first" and "second" bookings leave alike audit entries, the same notification and the same email

  Scenario: Passer le statut à `checked-in`, `fulfilled` ou `noshow` est réservé au praticien du RDV et à l'admin. (absence par l'admin, créneau libéré)
    When "admin" updates in FHIR the appointment of "first" with "status=noshow"
    Then the update answers "noshow"
    And the "clinician" slot at "09:00" is free again

  Scenario Outline: Passer le statut à `checked-in`, `fulfilled` ou `noshow` est réservé au praticien du RDV et à l'admin. (refus : <case>)
    When "<who>" updates in FHIR the appointment of "first" with "status=checked-in"
    Then the client is refused with 403 and the code "forbidden"
    And the application API answers the same to the same update
    And the appointment of "first" is still "BOOKED" at "09:00"

    Examples:
      | case             | who       |
      | patient          | first     |
      | autre praticien  | colleague |

  Scenario Outline: Tout autre changement de statut est refusé en 409 avec `invalid_transition` et le statut courant. (<case>)
    Given the appointment of "first" is "<status>"
    When "clinician" updates in FHIR the appointment of "first" with "status=<target>"
    Then the client is refused with 409 and the code "invalid_transition"
    And the refusal gives the current status "<status>"

    Examples:
      | case                    | status     | target    |
      | fin sans arrivée        | BOOKED     | fulfilled |
      | retour à réservé        | CHECKED_IN | booked    |
      | remise en proposition   | BOOKED     | proposed  |

  Scenario: Tout autre changement de statut est refusé en 409 avec `invalid_transition` et le statut courant. (comme par l'API)
    When "clinician" updates in FHIR the appointment of "first" with "status=fulfilled"
    Then the client is refused with 409 and the code "invalid_transition"
    And the application API answers the same to the same update

  Scenario: Une mise à jour avec un `If-Match` périmé échoue en 412.
    When "first" updates in FHIR the appointment of "first" with "start=11:00" at a stale version
    Then the client is refused with 412 and the code "conflict"
    And the appointment of "first" is still "BOOKED" at "09:00"

  Scenario: Les refus, l'audit, les notifications et les emails sont ceux des écrans dans les mêmes cas. (notes cliniques)
    When "clinician" updates in FHIR the appointment of "first" with "comment=Tension normale"
    Then the update answers "booked" with the notes "Tension normale"
    When "clinician" writes the notes "Tension normale" on the appointment file of "second"
    Then the "first" and "second" bookings leave alike audit entries, the same notification and the same email

  Scenario Outline: Les refus, l'audit, les notifications et les emails sont ceux des écrans dans les mêmes cas. (notes refusées : <case>)
    When "<who>" updates in FHIR the appointment of "first" with "comment=Tension normale"
    Then the client is refused with 403 and the code "forbidden"

    Examples:
      | case    | who   |
      | admin   | admin |
      | patient | first |
