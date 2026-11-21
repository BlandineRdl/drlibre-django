Feature: L'admin voit les RDV par jour et les praticiens les plus chargés
  En tant que admin
  Je veux la répartition des RDV par jour et les praticiens les plus chargés sur la période choisie
  Afin que je repère les pics d'activité et la charge de chacun

  Background:
    Given now is "2026-11-20T10:00:00+00:00"
    And the clinician "Dr Paris" works in "Europe/Paris"
    And the admin is signed in

  Scenario: Un histogramme montre, pour chaque jour de la période, le nombre de RDV non annulés qui y commencent, dans le fuseau de l'hôpital de chaque RDV
    Given the clinician "Dr Cayenne" works in "America/Cayenne"
    And "Dr Paris" has a "BOOKED" "ONLINE" appointment at "2026-11-18T09:00" for 30 minutes
    And "Dr Paris" has a "COMPLETED" "STAFF" appointment at "2026-11-18T10:00" for 30 minutes
    And "Dr Paris" has a "CANCELLED" "ONLINE" appointment at "2026-11-20T09:00" for 30 minutes
    And "Dr Cayenne" has a "BOOKED" "ONLINE" appointment at "2026-11-19T23:30" for 30 minutes
    When the admin views the dashboard for the range "7"
    Then the histogram reads "11-14:0, 11-15:0, 11-16:0, 11-17:0, 11-18:2, 11-19:1, 11-20:0"

  Scenario: Les 5 praticiens les plus chargés sont classés par nombre de RDV non annulés sur la période
    Given the clinicians "Dr F, Dr E, Dr D, Dr C, Dr B, Dr A" work in "Europe/Paris"
    And "Dr A" has appointments on the days "0, 1, 2" before today
    And "Dr B" has appointments on the days "0" before today
    And "Dr C" has appointments on the days "0, 1" before today
    And "Dr D" has appointments on the days "0, 1" before today
    And "Dr E" has appointments on the days "0" before today
    And "Dr F" has appointments on the days "0" before today
    And "Dr F" has a "CANCELLED" "ONLINE" appointment at "2026-11-20T15:00" for 30 minutes
    And "Dr F" has a "CANCELLED" "ONLINE" appointment at "2026-11-20T16:00" for 30 minutes
    When the admin views the dashboard for the range "7"
    Then the busiest clinicians read "Dr A:3, Dr C:2, Dr D:2, Dr B:1, Dr E:1"

  Scenario: Les 5 praticiens les plus chargés sont classés par nombre de RDV non annulés sur la période (moins de 5 praticiens occupés)
    Given the clinician "Dr Libre" works in "Europe/Paris"
    And "Dr Paris" has appointments on the days "0" before today
    When the admin views the dashboard for the range "7"
    Then the busiest clinicians read "Dr Paris:1"

  Scenario: L'histogramme et le classement suivent la période choisie pour les indicateurs
    Given "Dr Paris" has appointments on the days "0, 10" before today
    When the admin views the dashboard for the range "30"
    Then the histogram has 30 days counting 2 appointments
    And the busiest clinicians read "Dr Paris:2"
    When the admin views the dashboard for the range "today"
    Then the histogram reads "11-20:1"
    And the busiest clinicians read "Dr Paris:1"
