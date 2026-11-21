Feature: Le praticien fait avancer le statut d'un RDV
  En tant que praticien
  Je veux marquer un de mes RDV arrivé, terminé ou absent
  Afin que l'agenda et le reporting reflètent ce qui s'est passé

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And the signed-in clinician is "A"

  Scenario Outline: Un RDV `BOOKED` peut passer à `CHECKED_IN` ou `NO_SHOW` ; un RDV `CHECKED_IN` à `COMPLETED` ; `COMPLETED`, `CANCELLED` et `NO_SHOW` sont définitifs. (<case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the clinician applies "<action>" to it
    Then the appointment is now "<to>"

    Examples:
      | case                  | from       | action   | to         |
      | réservé puis arrivé   | BOOKED     | check_in | CHECKED_IN |
      | réservé puis absent   | BOOKED     | no_show  | NO_SHOW    |
      | arrivé puis terminé   | CHECKED_IN | complete | COMPLETED  |

  Scenario Outline: Un RDV `BOOKED` peut passer à `CHECKED_IN` ou `NO_SHOW` ; un RDV `CHECKED_IN` à `COMPLETED` ; `COMPLETED`, `CANCELLED` et `NO_SHOW` sont définitifs. (définitif : <case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the clinician applies "<action>" to it
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "<from>"
    And nothing was changed or notified

    Examples:
      | case                 | from      | action   |
      | terminé puis arrivé  | COMPLETED | check_in |
      | terminé puis absent  | COMPLETED | no_show  |
      | terminé puis terminé | COMPLETED | complete |
      | annulé puis arrivé   | CANCELLED | check_in |
      | annulé puis absent   | CANCELLED | no_show  |
      | annulé puis terminé  | CANCELLED | complete |
      | absent puis arrivé   | NO_SHOW   | check_in |
      | absent puis absent   | NO_SHOW   | no_show  |
      | absent puis terminé  | NO_SHOW   | complete |

  Scenario Outline: L'agenda du jour et la fiche ne proposent que les actions permises par le statut courant. (<case>)
    Given the patient has a "<status>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    Then the clinician is offered "<actions>"

    Examples:
      | case    | status     | actions                                  |
      | réservé | BOOKED     | check_in, no_show, cancel, reschedule    |
      | arrivé  | CHECKED_IN | complete, cancel                         |
      | terminé | COMPLETED  | nothing                                  |
      | annulé  | CANCELLED  | nothing                                  |
      | absent  | NO_SHOW    | nothing                                  |

  Scenario Outline: Une transition interdite renvoie `invalid_transition` avec le statut courant. (<case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the clinician applies "<action>" to it
    Then the booking is refused as "invalid_transition"
    And the refusal names the status "<from>"
    And nothing was changed or notified

    Examples:
      | case                     | from       | action   |
      | réservé terminé d'emblée | BOOKED     | complete |
      | arrivé marqué absent     | CHECKED_IN | no_show  |
      | arrivé marqué arrivé     | CHECKED_IN | check_in |

  Scenario Outline: Ces changements ne notifient pas le patient. (<case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the clinician applies "<action>" to it
    Then the appointment is now "<to>"
    And no one was notified

    Examples:
      | case    | from       | action   | to         |
      | arrivé  | BOOKED     | check_in | CHECKED_IN |
      | absent  | BOOKED     | no_show  | NO_SHOW    |
      | terminé | CHECKED_IN | complete | COMPLETED  |

  Scenario: Sur le RDV d'un autre praticien, l'action est refusée avec `forbidden`.
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And the signed-in clinician is "B"
    When the clinician applies "check_in" to it
    Then the booking is refused as "forbidden"
    And nothing was changed or notified

  Scenario: Règle §9 : seul un praticien ayant un profil fait avancer un RDV
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And the signed-in user holds no clinician profile
    When the clinician applies "check_in" to it
    Then the booking is refused as "forbidden"
    And nothing was changed or notified

  Scenario: Règle §4 : un RDV inconnu est introuvable
    When the clinician applies "check_in" to an unknown appointment
    Then the booking is refused as "not_found"

  Scenario: Règle §5.6 : un RDV marqué absent libère son créneau
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the clinician applies "no_show" to it
    Then the slots of "A" were refreshed

  Scenario Outline: Chaque changement laisse une entrée d'audit avec l'ancien et le nouveau statut, sans donnée personnelle. (<case>)
    Given the patient has a "<from>" appointment with "A" at "2026-11-20 14:00" in room "R1"
    When the clinician applies "<action>" to it
    Then the audit records the change from "<from>" to "<to>" by the clinician, with no personal data

    Examples:
      | case    | from       | action   | to         |
      | arrivé  | BOOKED     | check_in | CHECKED_IN |
      | absent  | BOOKED     | no_show  | NO_SHOW    |
      | terminé | CHECKED_IN | complete | COMPLETED  |
