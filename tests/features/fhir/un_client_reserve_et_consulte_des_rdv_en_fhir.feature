Feature: Un client réserve et consulte des RDV en FHIR
  En tant que client API agissant pour un patient, un praticien ou un admin
  Je veux réserver un créneau et retrouver les RDV de mon utilisateur
  Afin que mon application gère la prise de RDV sous les mêmes règles que les écrans

  Background:
    Given a bookable department with two clinicians, one room, two patients and an admin

  Scenario: Créer un `Appointment` au statut `proposed` avec le patient, le `serviceType` et soit une référence `slot`, soit un début et un praticien, renvoie un `Appointment` `booked` avec le praticien et la salle attribués ; la fin est toujours calculée par le serveur. (référence slot)
    When "first" books in FHIR at "09:00" with "slot=clinician, patient=first"
    Then the appointment is created "booked" with "clinician", the room, the end at "09:30" and the source "ONLINE"

  Scenario: Créer un `Appointment` au statut `proposed` avec le patient, le `serviceType` et soit une référence `slot`, soit un début et un praticien, renvoie un `Appointment` `booked` avec le praticien et la salle attribués ; la fin est toujours calculée par le serveur. (début et praticien, fin fournie ignorée)
    When "first" books in FHIR at "09:00" with "practitioner=clinician, end=11:00"
    Then the appointment is created "booked" with "clinician", the room, the end at "09:30" and the source "ONLINE"

  Scenario Outline: Créer un `Appointment` au statut `proposed` avec le patient, le `serviceType` et soit une référence `slot`, soit un début et un praticien, renvoie un `Appointment` `booked` avec le praticien et la salle attribués ; la fin est toujours calculée par le serveur. (refus : <case>)
    When "first" books in FHIR at "09:00" with "<fields>"
    Then the client is refused with 400 and the code "invalid_input"
    And the application API answers the same to the same booking

    Examples:
      | case                           | fields                                    |
      | un motif saisi à la création   | practitioner=clinician, reason=Douleur    |
      | un autre statut que proposé    | practitioner=clinician, status=booked     |

  Scenario: Sans praticien, un patient obtient le premier disponible (round robin, source `ROUND_ROBIN`) ; le personnel doit nommer un praticien. (patient)
    When "first" books in FHIR at "09:00" with ""
    Then the appointment is created "booked" with a clinician of the department and the source "ROUND_ROBIN"

  Scenario: Sans praticien, un patient obtient le premier disponible (round robin, source `ROUND_ROBIN`) ; le personnel doit nommer un praticien. (personnel)
    When "admin" books in FHIR at "09:00" with "patient=first"
    Then the client is refused with 400 and the code "invalid_input"
    And the application API answers the same to the same booking

  Scenario Outline: Les droits sont ceux du §5.4 : le patient pour lui-même et sans salle, le praticien dans son agenda pour un patient actif, l'admin pour tout patient actif ; source `ONLINE`, `ROUND_ROBIN` ou `STAFF` comme à l'écran. (<case>)
    When "<who>" books in FHIR at "09:00" with "<fields>"
    Then the appointment is created "booked" with "<clinician>", the room, the end at "09:30" and the source "<source>"

    Examples:
      | case                         | who       | fields                                       | clinician | source |
      | le patient pour lui-même     | first     | practitioner=clinician, patient=first        | clinician | ONLINE |
      | le praticien dans son agenda | clinician | practitioner=clinician, patient=first        | clinician | STAFF  |
      | l'admin pour tout patient    | admin     | practitioner=colleague, patient=second, room=room | colleague | STAFF  |

  Scenario Outline: Les droits sont ceux du §5.4 : le patient pour lui-même et sans salle, le praticien dans son agenda pour un patient actif, l'admin pour tout patient actif ; source `ONLINE`, `ROUND_ROBIN` ou `STAFF` comme à l'écran. (refus : <case>)
    When "<who>" books in FHIR at "09:00" with "<fields>"
    Then the client is refused with <status> and the code "<code>"
    And the application API answers the same to the same booking

    Examples:
      | case                            | who       | fields                                  | status | code      |
      | un patient pour un autre        | first     | practitioner=clinician, patient=second  | 403    | forbidden |
      | un patient qui choisit la salle | first     | practitioner=clinician, room=room       | 403    | forbidden |
      | un praticien hors de son agenda | clinician | practitioner=colleague, patient=first   | 403    | forbidden |
      | un patient inactif              | admin     | practitioner=clinician, patient=former  | 403    | forbidden |

  Scenario Outline: Les refus sont ceux des écrans dans les mêmes cas : `not_found`, `conflict` avec les ressources en cause, `rule_violation` avec les règles violées, `no_room_available`, `no_clinician_available`, en `OperationOutcome`. (<case>)
    Given "second" has booked "<taken>" at "09:00"
    When "first" books in FHIR at "<start>" with "<fields>"
    Then the client is refused with <status> and the code "<code>"
    And the application API answers the same to the same booking

    Examples:
      | case                        | taken     | start | fields                              | status | code                   |
      | un créneau déjà pris        | clinician | 09:00 | practitioner=clinician              | 409    | conflict               |
      | hors des disponibilités     | nobody    | 13:00 | practitioner=clinician              | 422    | rule_violation         |
      | aucune salle libre          | clinician | 09:00 | practitioner=colleague              | 409    | no_room_available      |
      | aucun praticien disponible  | nobody    | 13:00 |                                     | 409    | no_clinician_available |
      | un type de RDV inconnu      | nobody    | 09:00 | practitioner=clinician, type=absent | 404    | not_found              |

  Scenario: La réservation laisse la même entrée d'audit et envoie la même notification et le même email qu'à l'écran.
    When "second" books "clinician" at "10:00" on the booking screen
    And "first" books in FHIR at "09:00" with "practitioner=clinician"
    Then the "first" and "second" bookings leave alike audit entries, the same notification and the same email

  Scenario: Lecture et recherche `Appointment` sont limitées aux RDV du patient, à l'agenda du praticien ou à tout pour l'admin, avec `patient`, `practitioner`, `location`, `status`, `date`, `service-type` et `_include` `Appointment:patient`, `Appointment:practitioner`, `Appointment:location`. (lecture)
    Given "first" has booked "clinician" at "09:00"
    And "second" has booked "colleague" at "10:00"
    When "first" reads the appointment of "first"
    Then the FHIR appointments found are "first 09:00"
    When "clinician" reads the appointment of "first"
    Then the FHIR appointments found are "first 09:00"
    When "admin" reads the appointment of "second"
    Then the FHIR appointments found are "second 10:00"
    When "first" reads the appointment of "second"
    Then the client is refused with 403 and the code "forbidden"
    When "clinician" reads the appointment of "second"
    Then the client is refused with 403 and the code "forbidden"
    When "first" reads the appointment of "absent"
    Then the client is refused with 404 and the code "not_found"
    When "nobody" reads the appointment of "first"
    Then the client is refused with 401 and the code "unauthenticated"

  Scenario: Lecture et recherche `Appointment` sont limitées aux RDV du patient, à l'agenda du praticien ou à tout pour l'admin, avec `patient`, `practitioner`, `location`, `status`, `date`, `service-type` et `_include` `Appointment:patient`, `Appointment:practitioner`, `Appointment:location`. (recherche)
    Given "first" has booked "clinician" at "09:00"
    And "second" has booked "colleague" at "10:00"
    When "first" searches the appointments with "_sort=date"
    Then the FHIR appointments found are "first 09:00"
    When "clinician" searches the appointments with "_include=Appointment:patient"
    Then the FHIR appointments found are "first 09:00"
    And the bundle includes the "Patient" "first"
    When "admin" searches the appointments with "practitioner=Practitioner/$colleague&_include=Appointment:practitioner"
    Then the FHIR appointments found are "second 10:00"
    And the bundle includes the "Practitioner" "colleague"
    When "admin" searches the appointments with "location=Location/$room&_include=Appointment:location&_sort=-date"
    Then the FHIR appointments found are "second 10:00, first 09:00"
    And the bundle includes the "Location" "room"
    When "admin" searches the appointments with "patient=Patient/$second"
    Then the FHIR appointments found are "second 10:00"
    When "admin" searches the appointments with "status=booked&service-type=$type&date=2026-11-23"
    Then the FHIR appointments found are "first 09:00, second 10:00"
    When "admin" searches the appointments with "date=lt2026-11-23T09:30:00%2B01:00"
    Then the FHIR appointments found are "first 09:00"
    When "admin" searches the appointments with "status=fulfilled"
    Then the FHIR appointments found are ""
    When "admin" searches the appointments with "status=arrived"
    Then the client is refused with 400 and the code "invalid_input"

  Scenario: Les statuts suivent le §15.3 : `BOOKED` → `booked` sans extension, `CHECKED_IN` → `checked-in`, `COMPLETED` → `fulfilled`, `CANCELLED` → `cancelled` avec `cancelationReason`, `NO_SHOW` → `noshow` ; la source est une extension et le motif du patient est `reasonCode.text`.
    Given "first" has an appointment and a waitlist entry in every status
    When "admin" searches the appointments with "patient=Patient/$first&_count=100"
    Then the FHIR statuses are "booked, checked-in, fulfilled, cancelled, noshow, waitlist, proposed, cancelled"
    And the booked appointment carries only the source extension "ONLINE" and the reason text "Douleur"
    And the cancelled appointment carries its cancellation reason "Empêchement"
    And the proposed entry shows the offered start and practitioner

  Scenario: Les notes cliniques (`Appointment.comment`) ne sont renvoyées qu'au praticien du RDV.
    Given "first" has booked "clinician" at "09:00" with the clinical notes "Tension normale"
    When "clinician" reads the appointment of "first"
    Then the appointment shows the notes "Tension normale"
    When "admin" reads the appointment of "first"
    Then the appointment shows no notes
    When "first" reads the appointment of "first"
    Then the appointment shows no notes
    When "colleague" searches the appointments with ""
    Then the FHIR appointments found are ""

  Scenario: Une retenue de réservation apparaît en `Appointment` `pending` pour le personnel seulement.
    Given a visitor holds "clinician" at "11:00" and an older hold has expired
    When "clinician" searches the appointments with "status=pending"
    Then the FHIR appointments found are "hold 11:00"
    When "admin" searches the appointments with "status=pending"
    Then the FHIR appointments found are "hold 11:00"
    When "colleague" searches the appointments with "status=pending"
    Then the FHIR appointments found are ""
    When "first" searches the appointments with "status=pending"
    Then the FHIR appointments found are ""
    When "first" reads the appointment of "hold"
    Then the client is refused with 403 and the code "forbidden"
