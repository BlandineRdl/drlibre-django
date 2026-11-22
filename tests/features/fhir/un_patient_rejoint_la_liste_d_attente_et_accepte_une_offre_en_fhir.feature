Feature: Un patient rejoint la liste d'attente et accepte une offre en FHIR
  En tant que client API agissant pour un patient ou un admin
  Je veux inscrire un patient sur la liste d'attente et accepter le créneau offert
  Afin que mon application profite des créneaux libérés

  Background:
    Given a bookable department with two clinicians, one room, two patients and an admin

  Scenario: Créer un `Appointment` au statut `waitlist` avec le `serviceType`, un `requestedPeriod` et éventuellement un praticien préféré inscrit le patient ; le patient s'inscrit lui-même, l'admin inscrit tout patient, un praticien reçoit `forbidden`. (le patient s'inscrit)
    When "first" joins the waitlist in FHIR with "from=2026-11-23, to=2026-11-24"
    Then the waitlist entry of "first" is created "waitlist" from "2026-11-23" to "2026-11-24" with no practitioner
    And the join is audited "booking.waitlist_joined" by "first"

  Scenario: Créer un `Appointment` au statut `waitlist` avec le `serviceType`, un `requestedPeriod` et éventuellement un praticien préféré inscrit le patient ; le patient s'inscrit lui-même, l'admin inscrit tout patient, un praticien reçoit `forbidden`. (l'admin inscrit un patient avec un praticien préféré)
    When "admin" joins the waitlist in FHIR with "patient=first, practitioner=colleague, from=2026-11-23, to=2026-11-23"
    Then the waitlist entry of "first" is created "waitlist" from "2026-11-23" to "2026-11-23" with "colleague"
    And the join is audited "booking.waitlist_joined" by "admin"

  Scenario Outline: Créer un `Appointment` au statut `waitlist` avec le `serviceType`, un `requestedPeriod` et éventuellement un praticien préféré inscrit le patient ; le patient s'inscrit lui-même, l'admin inscrit tout patient, un praticien reçoit `forbidden`. (refus : <case>)
    When "<who>" joins the waitlist in FHIR with "<asked>"
    Then the client is refused with <answer> and the code "<code>"
    And the application API answers the same to the same join
    And nobody waits on the waitlist

    Examples:
      | case                          | who       | asked                                          | answer | code      |
      | praticien                     | clinician | from=2026-11-23, to=2026-11-24                 | 403    | forbidden |
      | patient qui en inscrit un autre | first     | patient=second, from=2026-11-23, to=2026-11-24 | 403    | forbidden |
      | patient inactif               | admin     | patient=former, from=2026-11-23, to=2026-11-24 | 404    | not_found |
      | praticien qui nomme un praticien préféré inconnu | clinician | practitioner=unknown, from=2026-11-23, to=2026-11-24 | 403 | forbidden |

  Scenario Outline: Un type inactif ou un praticien préféré inactif donne `not_found`. (<case>)
    Given the <inactive> is inactive
    When "first" joins the waitlist in FHIR with "practitioner=colleague, from=2026-11-23, to=2026-11-24"
    Then the client is refused with 404 and the code "not_found"
    And the application API answers the same to the same join
    And nobody waits on the waitlist

    Examples:
      | case               | inactive              |
      | type inactif       | waitlisted appointment type |
      | praticien inactif  | "colleague" clinician |

  Scenario: Les statuts suivent le §15.3 : `WAITING` → `waitlist`, `OFFERED` → `proposed` avec le début, la fin et le praticien offerts, `EXPIRED` → `cancelled`.
    Given "second" has booked "clinician" at "09:00"
    And "first" waits for a slot on Monday
    When "first" reads the waitlist entry of "first"
    Then the entry reads "waitlist" with no start
    Given "second" has cancelled their appointment on the application API
    When "first" reads the waitlist entry of "first"
    Then the entry reads "proposed" from "09:00" to "09:30" with "clinician"
    Given the clock is at "2026-11-23T17:05:00Z"
    And the waitlist expiry has run
    When "first" reads the waitlist entry of "first"
    Then the entry reads "cancelled" with no start

  Scenario Outline: Créer un `AppointmentResponse` au statut `accepted` sur une offre accepte celle-ci, pour le patient sur sa propre offre ou pour l'admin ; le placement, les règles et les refus sont ceux de l'écran, `conflict` compris si le créneau est déjà pris. (<case>)
    Given "second" has booked "clinician" at "09:00"
    And "first" waits for a slot on Monday
    And "second" has cancelled their appointment on the application API
    When "<who>" accepts in FHIR the offer of "first"
    Then the response is created "accepted" for "first"
    And the waitlist entry of "first" is booked with "clinician" at "09:00" for the source "<source>"

    Examples:
      | case                  | who   | source |
      | le patient            | first | ONLINE |
      | l'admin pour lui      | admin | STAFF  |

  Scenario Outline: Créer un `AppointmentResponse` au statut `accepted` sur une offre accepte celle-ci, pour le patient sur sa propre offre ou pour l'admin ; le placement, les règles et les refus sont ceux de l'écran, `conflict` compris si le créneau est déjà pris. (refus : <case>)
    Given "second" has booked "clinician" at "09:00"
    And "first" waits for a slot on Monday
    And "second" has cancelled their appointment on the application API
    And the waitlist entry of "first" is "<status>"
    When "<who>" accepts in FHIR the offer of "first"
    Then the client is refused with <answer> and the code "<code>"
    And the application API answers the same to the same acceptance

    Examples:
      | case                    | who       | status  | answer | code               |
      | offre d'un autre patient | second    | OFFERED | 403    | forbidden          |
      | praticien               | clinician | OFFERED | 403    | forbidden          |
      | entrée non proposée     | first     | WAITING | 409    | invalid_transition |

  Scenario: Créer un `AppointmentResponse` au statut `accepted` sur une offre accepte celle-ci, pour le patient sur sa propre offre ou pour l'admin ; le placement, les règles et les refus sont ceux de l'écran, `conflict` compris si le créneau est déjà pris. (créneau déjà pris)
    Given "second" has booked "clinician" at "09:00"
    And "first" waits for a slot on Monday
    And "second" has cancelled their appointment on the application API
    And "second" has booked "clinician" at "09:00"
    When "first" accepts in FHIR the offer of "first"
    Then the client is refused with 409 and the code "conflict"
    When "first" reads the waitlist entry of "first"
    Then the entry reads "waitlist" with no start

  Scenario: Après acceptation, la même ressource devient le RDV `booked` : une seule ressource, pas deux.
    Given "second" has booked "clinician" at "09:00"
    And "first" waits for a slot on Monday
    And "second" has cancelled their appointment on the application API
    When "first" accepts in FHIR the offer of "first"
    And "first" reads the waitlist entry of "first"
    Then the entry reads "booked" from "09:00" to "09:30" with "clinician"
    And the appointments of "first" are that one resource only

  Scenario Outline: `AppointmentResponse` est lisible par le patient (les siennes) et par l'admin. (<case>)
    Given "second" has booked "clinician" at "09:00"
    And "first" waits for a slot on Monday
    And "second" has cancelled their appointment on the application API
    And "first" has accepted in FHIR the offer of "first"
    When "<who>" reads the response of "first"
    Then the client is answered <answer>
    When "<who>" searches the responses
    Then the responses found are "<found>"

    Examples:
      | case              | who       | answer | found |
      | le patient        | first     | 200    | first |
      | l'admin           | admin     | 200    | first |
      | un autre patient  | second    | 403    |       |
      | le praticien      | clinician | 403    |       |

  Scenario: L'audit, les notifications et les emails sont ceux des écrans.
    Given "first" has booked "clinician" at "09:00"
    And "second" has booked "clinician" at "10:00"
    And "first" waits for a slot on Monday
    And "second" waits for a slot on Monday
    And "first" has cancelled their appointment on the application API
    And "second" has cancelled their appointment on the application API
    When "first" accepts in FHIR the offer of "first"
    And "second" accepts on the application API the offer of "second"
    Then the acceptances of "first" and "second" leave alike audit entries, the same notification and the same email
