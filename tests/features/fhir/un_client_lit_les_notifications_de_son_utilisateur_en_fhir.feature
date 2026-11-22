Feature: Un client lit les notifications de son utilisateur en FHIR
  En tant que client API agissant pour un patient
  Je veux lire les notifications du patient et les marquer comme lues
  Afin que mon application le tienne informé comme le portail

  Background:
    Given a bookable department with two clinicians, one room, two patients and an admin
    And "first" has booked "clinician" at "09:00"
    And "first" has cancelled their appointment on the application API
    And "second" has booked "clinician" at "10:00"

  Scenario: Chaque notification est une `Communication` avec destinataire, catégorie (le type de notification), texte, `sent`, `received` (heure de lecture) et `about` le RDV.
    When "first" searches the communications with ""
    Then the communications found are "RDV réservé, RDV annulé"
    And each communication of "first" carries its notification's recipient, kind, title, body, sending, reading and appointment

  Scenario Outline: Seul le destinataire lit ses `Communication` ; celle d'un autre donne `forbidden`. (<case>)
    When "<who>" reads the communication "RDV réservé" of "first"
    Then the client is answered <answer>

    Examples:
      | case             | who       | answer |
      | le destinataire  | first     | 200    |
      | un autre patient | second    | 403    |
      | l'admin          | admin     | 403    |
      | un praticien     | clinician | 403    |

  Scenario: Seul le destinataire lit ses `Communication` ; celle d'un autre donne `forbidden`. (un autre ne les trouve pas)
    When "second" searches the communications with "recipient=Patient/$first"
    Then the communications found are ""

  Scenario Outline: Les recherches acceptent `recipient`, `category` et `sent`. (<case>)
    When "first" searches the communications with "<query>"
    Then the communications found are "<found>"

    Examples:
      | case         | query                                 | found                   |
      | destinataire | recipient=Patient/$first              | RDV réservé, RDV annulé |
      | catégorie    | category=APPOINTMENT_CANCELLED        | RDV annulé              |
      | envoi        | sent=ge2026-11-20&sent=lt2026-11-21   | RDV réservé, RDV annulé |
      | envoi passé  | sent=lt2026-11-20                     |                         |

  Scenario: Le destinataire peut renseigner `received` pour marquer une notification comme lue ; aucune création ni suppression n'est acceptée. (lue en FHIR, lue au portail)
    When "first" fills in FHIR the reading of "RDV réservé"
    Then the client is answered 200
    And the communication "RDV réservé" of "first" reads received at the time of the reading
    And the portal notifications of "first" show "RDV réservé" read and "RDV annulé" unread
    And the reading is audited "notification.read" by "first"

  Scenario Outline: Le destinataire peut renseigner `received` pour marquer une notification comme lue ; aucune création ni suppression n'est acceptée. (refus : <case>)
    Given <before>
    When "<who>" sends in FHIR the communication "RDV réservé" of "first" with "<change>"
    Then the client is refused with <answer> and the code "<code>"
    And the communication "RDV réservé" of "first" is <state>

    Examples:
      | case                  | before                                         | who    | change            | answer | code          | state  |
      | un autre patient      | nothing more                                   | second | received          | 403    | forbidden     | unread |
      | texte changé          | nothing more                                   | first  | received, payload | 400    | invalid_input | unread |
      | déjà lue              | "first" has read "RDV réservé" on the portal   | first  | received later    | 400    | invalid_input | read   |
      | version périmée       | nothing more                                   | first  | received, stale   | 412    | conflict      | unread |

  Scenario Outline: Le destinataire peut renseigner `received` pour marquer une notification comme lue ; aucune création ni suppression n'est acceptée. (<case>)
    When "first" sends "<method>" to the communications with "<path>"
    Then the client is refused with 405 as not supported

    Examples:
      | case        | method | path                       |
      | création    | POST   | /fhir/Communication        |
      | suppression | DELETE | /fhir/Communication/$first |
