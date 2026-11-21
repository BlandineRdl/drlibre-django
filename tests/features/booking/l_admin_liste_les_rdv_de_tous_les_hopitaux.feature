Feature: L'admin liste les RDV de tous les hôpitaux
  En tant qu'admin
  Je veux filtrer les RDV de tous les hôpitaux
  Afin que je retrouve ceux sur lesquels intervenir

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And a signed-in admin
    And "A" works in "Cardiologie" at "Hôpital Nord" in "Europe/Paris"
    And "B" works in "Rythmologie" at "Hôpital du Lamentin" in "America/Martinique"
    And these appointments
      | name | clinician | start            | status    | source      |
      | a1   | A         | 2026-11-19 09:00 | COMPLETED | ONLINE      |
      | a2   | A         | 2026-11-20 14:00 | BOOKED    | STAFF       |
      | b1   | B         | 2026-11-20 13:00 | CANCELLED | ROUND_ROBIN |
      | b2   | B         | 2026-11-21 02:00 | BOOKED    | ONLINE      |

  Scenario Outline: Les filtres portent sur la période, le département, le praticien, le statut et la source, combinables. (<case>)
    When the admin lists the appointments with "<query>"
    Then the list shows "<shown>" out of <total>

    Examples:
      | case             | query                                  | shown      | total |
      | aucun filtre     |                                        | b2, a2, b1, a1 | 4 |
      | période          | start=2026-11-20&end=2026-11-20        | b2, a2, b1 | 3     |
      | département      | department=Rythmologie                 | b2, b1     | 2     |
      | praticien        | clinician=A                            | a2, a1     | 2     |
      | statut           | status=BOOKED                          | b2, a2     | 2     |
      | source           | source=ONLINE                          | b2, a1     | 2     |
      | filtres combinés | status=BOOKED&department=Cardiologie   | a2         | 1     |

  Scenario: Les RDV les plus récents viennent en premier, 20 par page avec le nombre total. (première page)
    Given 22 more "BOOKED" appointments of "A" one day apart from "2026-11-22 09:00"
    When the admin lists the appointments with "page=1"
    Then the list shows 20 appointments, the latest first, out of 26

  Scenario: Les RDV les plus récents viennent en premier, 20 par page avec le nombre total. (dernière page)
    Given 22 more "BOOKED" appointments of "A" one day apart from "2026-11-22 09:00"
    When the admin lists the appointments with "page=2"
    Then the list shows 6 appointments, the latest first, out of 26
    And the list ends with "b2, a2, b1, a1"

  Scenario Outline: Une valeur de filtre ou de page inutilisable dans l'adresse revient au défaut. (<case>)
    When the admin lists the appointments with "<query>"
    Then the list shows "b2, a2, b1, a1" out of 4

    Examples:
      | case                 | query                         |
      | date illisible       | start=demain&end=2026-13-40   |
      | identifiant illisible | department=x&clinician=12    |
      | statut inconnu       | status=CONFIRMED&source=SMS   |
      | page illisible       | page=-3                       |

  Scenario: Les heures sont affichées dans le fuseau de l'hôpital de chaque RDV, et la page indique ce fuseau.
    When the admin lists the appointments with ""
    Then the row "b2" is in "America/Martinique" at "Hôpital du Lamentin"
    And the row "a2" is in "Europe/Paris" at "Hôpital Nord"

  Scenario: Les heures sont affichées dans le fuseau de l'hôpital de chaque RDV, et la page indique ce fuseau. (jour local de l'hôpital)
    When the admin lists the appointments with "start=2026-11-21&end=2026-11-21"
    Then the list shows "" out of 0

  Scenario: Règle §10 : seul l'admin liste les RDV de tous les hôpitaux
    When the patient lists every appointment
    Then the booking is refused as "forbidden"
