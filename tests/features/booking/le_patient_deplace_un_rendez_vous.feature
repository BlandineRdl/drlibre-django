Feature: Le patient déplace un rendez-vous
  En tant que patient connecté, avec ou sans mot de passe
  Je veux déplacer un RDV vers un autre créneau du même praticien
  Afin que je garde mon RDV quand l'heure ne me convient plus

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2, R3" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And the patient has a "BOOKED" appointment with "A" at "2026-11-23 09:00" in room "R2"
    And "A" is free at "2026-11-23 10:00"

  Scenario Outline: Seul un RDV `BOOKED` se déplace ; l'action « Déplacer » n'est proposée que quand les règles la permettent. (<case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-23 09:00" in room "R2"
    When the patient moves it to "2026-11-23 10:00"
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "<status>"
    And nothing was changed or notified

    Examples:
      | case        | status     |
      | arrivé      | CHECKED_IN |
      | terminé     | COMPLETED  |
      | annulé      | CANCELLED  |
      | absent      | NO_SHOW    |

  Scenario Outline: Seul un RDV `BOOKED` se déplace ; l'action « Déplacer » n'est proposée que quand les règles la permettent. (proposée : <case>)
    Given the patient has a "<status>" appointment with "A" at "<start>" in room "R2"
    Then the patient is offered "<actions>"

    Examples:
      | case                       | status     | start            | actions            |
      | réservé dans plus de 24 h  | BOOKED     | 2026-11-23 09:00 | cancel, reschedule |
      | arrivé                     | CHECKED_IN | 2026-11-23 09:00 | cancel             |
      | réservé dans moins de 24 h | BOOKED     | 2026-11-21 09:00 | nothing            |

  Scenario: Un bandeau à la semaine propose les créneaux libres du même praticien pour le même type ; la fin est recalculée, jamais reçue de l'appelant. (fin recalculée)
    When the patient moves it to "2026-11-23 10:00"
    Then the appointment is "BOOKED" from "2026-11-23 10:00" for 30 minutes in room "R2"
    And the move offers no way to name an end time

  Scenario Outline: Refus en `rule_violation` avec les règles violées : RDV actuel à moins de 24 h (`cancellation_window_closed`), nouveau début à moins de 120 min (`lead_time_too_short`), type non réservable en ligne (`type_not_bookable_online`), début hors des créneaux libres (`outside_availability`). (<case>)
    Given the patient has a "BOOKED" appointment with "A" at "<current>" in room "R2"
    And "A" is free at "2026-11-20 11:00"
    And the appointment type is <online>
    When the patient moves it to "<start>"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "<rules>"
    And nothing was changed or notified

    Examples:
      | case                         | current          | online                       | start            | rules                                                                                          |
      | RDV actuel à moins de 24 h   | 2026-11-21 09:00 | bookable online              | 2026-11-23 10:00 | cancellation_window_closed                                                                     |
      | nouveau début trop proche    | 2026-11-23 09:00 | bookable online              | 2026-11-20 11:00 | lead_time_too_short                                                                            |
      | type non réservable en ligne | 2026-11-23 09:00 | not bookable online          | 2026-11-23 10:00 | type_not_bookable_online                                                                       |
      | début hors des créneaux      | 2026-11-23 09:00 | bookable online              | 2026-11-23 10:15 | outside_availability                                                                           |
      | toutes les règles, en ordre  | 2026-11-21 09:00 | not bookable online          | 2026-11-20 11:15 | cancellation_window_closed, lead_time_too_short, type_not_bookable_online, outside_availability |

  Scenario: Un chevauchement avec un autre RDV du patient, du praticien ou de la salle donne `conflict` avec les ressources en cause ; le RDV déplacé est ignoré. (autre RDV du patient)
    Given the patient has an active appointment with "B" from "2026-11-23 10:15" to "2026-11-23 10:45"
    When the patient moves it to "2026-11-23 10:00"
    Then the booking is refused as "conflict"
    And the refusal names the resources "patient"
    And nothing was changed or notified

  Scenario: Un chevauchement avec un autre RDV du patient, du praticien ou de la salle donne `conflict` avec les ressources en cause ; le RDV déplacé est ignoré. (autre RDV du praticien)
    Given "A" has an active appointment from "2026-11-23 10:15" to "2026-11-23 10:45"
    When the patient moves it to "2026-11-23 10:00"
    Then the booking is refused as "conflict"
    And the refusal names the resources "clinician"
    And nothing was changed or notified

  Scenario: Un chevauchement avec un autre RDV du patient, du praticien ou de la salle donne `conflict` avec les ressources en cause ; le RDV déplacé est ignoré. (créneau retenu pour un visiteur)
    Given the visitor asks to hold "A" at "2026-11-23 10:00"
    When the patient moves it to "2026-11-23 10:00"
    Then the booking is refused as "conflict"
    And the refusal names the resources "clinician"

  Scenario: Un chevauchement avec un autre RDV du patient, du praticien ou de la salle donne `conflict` avec les ressources en cause ; le RDV déplacé est ignoré. (RDV déplacé ignoré)
    Given "A" is free at "2026-11-23 09:15" once the appointment is ignored
    When the patient moves it to "2026-11-23 09:15"
    Then the appointment is "BOOKED" from "2026-11-23 09:15" for 30 minutes in room "R2"

  Scenario Outline: La salle actuelle est gardée si elle est libre, sinon la salle par défaut du praticien, sinon la première salle libre du département ; aucune salle libre donne `no_room_available`. (<case>)
    Given the rooms "<busy>" are used by someone else from "2026-11-23 10:00" to "2026-11-23 10:30"
    When the patient moves it to "2026-11-23 10:00"
    Then the appointment is "BOOKED" from "2026-11-23 10:00" for 30 minutes in room "<room>"

    Examples:
      | case                                   | busy   | room |
      | salle actuelle libre                   | R1     | R2   |
      | salle actuelle prise                   | R2     | R1   |
      | salles actuelle et par défaut prises   | R2, R1 | R3   |

  Scenario: La salle actuelle est gardée si elle est libre, sinon la salle par défaut du praticien, sinon la première salle libre du département ; aucune salle libre donne `no_room_available`. (aucune salle libre)
    Given the rooms "R1, R2, R3" are used by someone else from "2026-11-23 10:00" to "2026-11-23 10:30"
    When the patient moves it to "2026-11-23 10:00"
    Then the booking is refused as "no_room_available"
    And nothing was changed or notified

  Scenario: La notification « RDV déplacé » porte la nouvelle heure et est créée dans la même transaction ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion. Un déplacement refusé ne notifie rien. (déplacement accepté)
    When the patient moves it to "2026-11-23 10:00"
    Then the patient has one "RDV déplacé" notification about the appointment at "23/11/2026 à 11:00"
    And one email "Votre rendez-vous est déplacé" names the time, hospital and provider, without the reason, linking only to the sign-in page

  Scenario: La notification « RDV déplacé » porte la nouvelle heure et est créée dans la même transaction ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion. Un déplacement refusé ne notifie rien. (déplacement refusé)
    When the patient moves it to "2026-11-23 10:15"
    Then nothing was changed or notified

  Scenario: Le déplacement laisse une entrée d'audit sans donnée personnelle.
    When the patient moves it to "2026-11-23 10:00"
    Then the audit entry "booking.appointment_rescheduled" has the patient as actor and holds no personal data

  Scenario: Règle §12.3 : le RDV d'un autre patient est refusé en `forbidden`, un RDV inconnu en `not_found`
    Given the appointment belongs to another patient
    When the patient moves it to "2026-11-23 10:00"
    Then the booking is refused as "forbidden"
    And nothing was changed or notified
    When the patient moves an unknown appointment to "2026-11-23 10:00"
    Then the booking is refused as "not_found"
