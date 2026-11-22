Feature: Le praticien gère ses disponibilités en FHIR
  En tant que client API agissant pour un praticien
  Je veux gérer ses plages en `Schedule` et ses absences dans `PractitionerRole.notAvailable`
  Afin que son agenda se tienne depuis un outil externe

  Background:
    Given a reference directory of active and closed hospitals, their departments, rooms, types, specialties and clinicians
    And on "2026-11-20" the clinician is booked at "10:00" on "2026-11-23" and a colleague works in another department

  Scenario: Chaque plage est un `Schedule` dont les acteurs sont le praticien et la salle, l'horizon la période de validité, et le jour, les heures et le pas une extension ; elle est reflétée en lecture seule dans `PractitionerRole.availableTime`.
    When "clinician" creates a schedule on "tue" from "14:00" to "15:00" every 30 minutes in "$room"
    Then the client is answered 201 with the schedule of "clinician" in "$room" on "tue" from "14:00:00" to "15:00:00" every 30 minutes
    And the written schedule runs from "2026-11-20" with no end
    And the role "$profile" shows the hours "mon 09:00:00-12:00:00, tue 14:00:00-15:00:00"

  Scenario Outline: Chaque plage est un `Schedule` dont les acteurs sont le praticien et la salle, l'horizon la période de validité, et le jour, les heures et le pas une extension ; elle est reflétée en lecture seule dans `PractitionerRole.availableTime`. (horizon fixé <case>)
    When "clinician" <action> with the horizon "2026-12-01"
    Then the answer is 400 with an OperationOutcome "invalid" and the code "invalid_input"
    And the outcome names only the field "Schedule.planningHorizon"

    Examples:
      | case               | action                     |
      | à la création      | creates a schedule         |
      | à la modification  | updates the schedule $rule |

  Scenario: Chaque plage est un `Schedule` dont les acteurs sont le praticien et la salle, l'horizon la période de validité, et le jour, les heures et le pas une extension ; elle est reflétée en lecture seule dans `PractitionerRole.availableTime`. (heures changées par le rôle)
    When "clinician" changes the hours of their role to "tue 14:00:00-15:00:00" under its version
    Then the client is refused with 403 and the code "forbidden"
    And no availability audit entry was left

  Scenario: Le praticien crée, modifie et supprime ses propres `Schedule` ; ceux d'un autre donnent `forbidden`.
    When "clinician" creates a schedule on "tue" from "14:00" to "15:00" every 30 minutes in "$room"
    Then the FHIR slots of "2026-11-24" are "14:00 free, 14:30 free"
    When "clinician" moves the end of the written schedule to "16:00" under its version
    Then the client is answered 200 with the schedule of "clinician" in "$room" on "tue" from "14:00:00" to "16:00:00" every 30 minutes
    And the FHIR slots of "2026-11-24" are "14:00 free, 14:30 free, 15:00 free, 15:30 free"
    When "clinician" deletes the written schedule
    Then the client is answered 204 and the written schedule is gone
    And the FHIR slots of "2026-11-24" are ""

  Scenario Outline: Le praticien crée, modifie et supprime ses propres `Schedule` ; ceux d'un autre donnent `forbidden`. (<case>)
    When "<who>" sends "<method>" to "<path>" with a schedule of "<named>"
    Then the client is refused with 403 and the code "forbidden"
    And no availability audit entry was left

    Examples:
      | case                                 | who       | method | path                           | named     |
      | modifier la plage d'un autre         | clinician | PUT    | /fhir/Schedule/$colleague_rule | colleague |
      | supprimer la plage d'un autre        | clinician | DELETE | /fhir/Schedule/$colleague_rule | colleague |
      | créer une plage au nom d'un autre    | clinician | POST   | /fhir/Schedule                 | colleague |
      | l'admin crée une plage               | admin     | POST   | /fhir/Schedule                 | admin     |
      | l'admin modifie la plage du praticien | admin    | PUT    | /fhir/Schedule/$rule           | clinician |

  Scenario Outline: Les règles sont celles de l'écran : salle active de son département, plages d'un même jour qui se touchent sans se chevaucher, pas de 5 à 240 minutes, fin après début. (<case>)
    When "clinician" creates a schedule on "<day>" from "<start>" to "<end>" every <step> minutes in "<room>"
    Then the answer is 400 with an OperationOutcome "invalid" and the code "invalid_input"
    And the outcome names only the field "<field>"
    And no availability audit entry was left

    Examples:
      | case                         | day | start | end   | step | room         | field        |
      | salle d'un autre département | tue | 14:00 | 15:00 | 30   | $other_room  | room_id      |
      | plages qui se chevauchent    | mon | 11:00 | 13:00 | 30   | $room        | start        |
      | pas sous 5 minutes           | tue | 14:00 | 15:00 | 4    | $room        | step_minutes |
      | pas au-delà de 240 minutes   | tue | 14:00 | 15:00 | 241  | $room        | step_minutes |
      | fin avant début              | tue | 15:00 | 14:00 | 30   | $room        | end          |

  Scenario: Les règles sont celles de l'écran : salle active de son département, plages d'un même jour qui se touchent sans se chevaucher, pas de 5 à 240 minutes, fin après début. (plages qui se touchent)
    When "clinician" creates a schedule on "mon" from "12:00" to "13:00" every 30 minutes in "$room"
    Then the client is answered 201 with the schedule of "clinician" in "$room" on "mon" from "12:00:00" to "13:00:00" every 30 minutes

  Scenario: Le praticien ajoute ou retire une absence en mettant à jour `notAvailable` de son propre `PractitionerRole`, sans pouvoir y changer autre chose ; une période identique déjà enregistrée est refusée.
    When "clinician" adds to their role the time off "Formation" from "2026-11-23T10:00:00+01:00" to "2026-11-23T11:00:00+01:00" under its version
    Then the client is answered 200 with the time offs "Congés, Formation"
    And the clinician's stored time offs are "Congés, Formation"
    When "clinician" removes from their role the time off "Formation" under its version
    Then the client is answered 200 with the time offs "Congés"
    And the clinician's stored time offs are "Congés"

  Scenario Outline: Le praticien ajoute ou retire une absence en mettant à jour `notAvailable` de son propre `PractitionerRole`, sans pouvoir y changer autre chose ; une période identique déjà enregistrée est refusée. (<case>)
    When "clinician" changes "<element>" of their role under its version
    Then the client is refused with 403 and the code "forbidden"
    And no availability audit entry was left

    Examples:
      | case                | element  |
      | présentation        | bio      |
      | statut              | active   |
      | salles et site      | location |

  Scenario: Le praticien ajoute ou retire une absence en mettant à jour `notAvailable` de son propre `PractitionerRole`, sans pouvoir y changer autre chose ; une période identique déjà enregistrée est refusée. (rôle d'un autre)
    When "clinician" adds to the role "$colleague_profile" the time off "Formation" from "2026-11-23T10:00:00+01:00" to "2026-11-23T11:00:00+01:00"
    Then the client is refused with 403 and the code "forbidden"
    And no availability audit entry was left

  Scenario: Le praticien ajoute ou retire une absence en mettant à jour `notAvailable` de son propre `PractitionerRole`, sans pouvoir y changer autre chose ; une période identique déjà enregistrée est refusée. (période identique)
    When "clinician" adds to their role the time off "Congés" from "2026-12-24T09:00:00+01:00" to "2026-12-26T19:00:00+01:00" under its version
    Then the answer is 400 with an OperationOutcome "invalid" and the code "invalid_input"
    And the outcome names only the field "start"
    And the clinician's stored time offs are "Congés"

  Scenario: Le praticien ajoute ou retire une absence en mettant à jour `notAvailable` de son propre `PractitionerRole`, sans pouvoir y changer autre chose ; une période identique déjà enregistrée est refusée. (une période refusée, aucune écrite)
    When "clinician" adds to their role the time offs "Formation" from "2026-11-23T10:00:00+01:00" to "2026-11-23T11:00:00+01:00" then "Congés" from "2026-12-24T09:00:00+01:00" to "2026-12-26T19:00:00+01:00"
    Then the answer is 400 with an OperationOutcome "invalid" and the code "invalid_input"
    And the clinician's stored time offs are "Congés"
    And no availability audit entry was left

  Scenario: Le praticien ajoute ou retire une absence en mettant à jour `notAvailable` de son propre `PractitionerRole`, sans pouvoir y changer autre chose ; une période identique déjà enregistrée est refusée. (version périmée)
    When "clinician" adds to their role the time off "Formation" from "2026-11-23T10:00:00+01:00" to "2026-11-23T11:00:00+01:00" under a stale version
    Then the client is refused with 412 and the code "conflict"
    And the clinician's stored time offs are "Congés"

  Scenario: Une absence n'annule pas les RDV déjà réservés ; les `Slot` reflètent aussitôt chaque changement.
    Then the FHIR slots of "2026-11-23" are "09:00 free, 09:15 free, 09:30 free, 10:30 free, 10:45 free, 11:00 free, 11:15 free, 11:30 free"
    When "clinician" adds to their role the time off "Formation" from "2026-11-23T10:00:00+01:00" to "2026-11-23T11:00:00+01:00" under its version
    Then the FHIR slots of "2026-11-23" are "09:00 free, 09:15 free, 09:30 free, 11:00 free, 11:15 free, 11:30 free"
    And the clinician's appointment at "10:00" on "2026-11-23" is still booked
    When "clinician" removes from their role the time off "Formation" under its version
    Then the FHIR slots of "2026-11-23" are "09:00 free, 09:15 free, 09:30 free, 10:30 free, 10:45 free, 11:00 free, 11:15 free, 11:30 free"

  Scenario Outline: Chaque écriture laisse la même entrée d'audit que l'écran. (<case>)
    When "clinician" <writes> in FHIR
    And "clinician" <writes> on the workspace
    Then both leave the same availability audit entries "<actions>" by "clinician"

    Examples:
      | case    | writes                                     | actions                                                                  |
      | plage   | creates, changes and deletes a schedule    | availability_rule.created, availability_rule.updated, availability_rule.deleted |
      | absence | adds and removes a time off                | time_off.created, time_off.deleted                                       |
