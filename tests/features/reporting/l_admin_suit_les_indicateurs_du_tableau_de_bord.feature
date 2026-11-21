Feature: L'admin suit les indicateurs du tableau de bord
  En tant que admin
  Je veux les indicateurs d'activité de tous les hôpitaux sur une période
  Afin que je mesure l'utilisation, les absences et la part de réservation en ligne

  Background:
    Given now is "2026-11-20T10:00:00+00:00"
    And the clinician "Dr Paris" works in "Europe/Paris"
    And the admin is signed in

  Scenario: La période vaut aujourd'hui, 7 jours ou 30 jours finissant aujourd'hui ; 7 jours par défaut ; une valeur inutilisable dans l'adresse revient au défaut (aujourd'hui)
    Given "Dr Paris" has appointments on the days "0, 6, 29" before today
    When the admin views the dashboard for the range "today"
    Then the range is "today"
    And the dashboard counts 1 appointments and 0 cancellations

  Scenario: La période vaut aujourd'hui, 7 jours ou 30 jours finissant aujourd'hui ; 7 jours par défaut ; une valeur inutilisable dans l'adresse revient au défaut (30 jours)
    Given "Dr Paris" has appointments on the days "0, 6, 29, 30" before today
    When the admin views the dashboard for the range "30"
    Then the range is "30"
    And the dashboard counts 3 appointments and 0 cancellations

  Scenario: La période vaut aujourd'hui, 7 jours ou 30 jours finissant aujourd'hui ; 7 jours par défaut ; une valeur inutilisable dans l'adresse revient au défaut (7 jours par défaut)
    Given "Dr Paris" has appointments on the days "0, 6, 7" before today
    When the admin views the dashboard without a range
    Then the range is "7"
    And the dashboard counts 2 appointments and 0 cancellations

  Scenario: La période vaut aujourd'hui, 7 jours ou 30 jours finissant aujourd'hui ; 7 jours par défaut ; une valeur inutilisable dans l'adresse revient au défaut (valeur inutilisable)
    Given "Dr Paris" has appointments on the days "0, 6, 7" before today
    When the admin views the dashboard for the range "14"
    Then the range is "7"
    And the dashboard counts 2 appointments and 0 cancellations

  Scenario: Un RDV compte dans la période si son début tombe dans un de ses jours, comptés dans le fuseau de l'hôpital du RDV
    Given now is "2026-11-21T01:00:00+00:00"
    And the clinician "Dr Cayenne" works in "America/Cayenne"
    And "Dr Cayenne" has a "BOOKED" "ONLINE" appointment at "2026-11-20T23:30" for 30 minutes
    And "Dr Paris" has a "BOOKED" "ONLINE" appointment at "2026-11-20T23:30" for 30 minutes
    When the admin views the dashboard for the range "today"
    Then the dashboard counts 1 appointments and 0 cancellations

  Scenario: RDV : RDV non annulés. Annulations : RDV annulés.
    Given "Dr Paris" has a "BOOKED" "ONLINE" appointment at "2026-11-20T09:00" for 30 minutes
    And "Dr Paris" has a "COMPLETED" "STAFF" appointment at "2026-11-20T09:30" for 30 minutes
    And "Dr Paris" has a "NO_SHOW" "ONLINE" appointment at "2026-11-20T10:00" for 30 minutes
    And "Dr Paris" has a "CANCELLED" "ONLINE" appointment at "2026-11-20T10:30" for 30 minutes
    When the admin views the dashboard for the range "today"
    Then the dashboard counts 3 appointments and 1 cancellations

  Scenario: Utilisation : minutes des RDV actifs dans la période ÷ minutes disponibles, soit les heures des plages des praticiens actifs sur la période moins leurs absences
    Given "Dr Paris" has a rule on weekday 5 from "09:00" to "12:00"
    And "Dr Paris" is off from "2026-11-20T11:00" to "2026-11-20T13:00"
    And the inactive clinician "Dr Parti" in "Europe/Paris" has a rule on weekday 5 from "09:00" to "12:00"
    And "Dr Paris" has a "BOOKED" "ONLINE" appointment at "2026-11-20T09:00" for 30 minutes
    And "Dr Paris" has a "COMPLETED" "STAFF" appointment at "2026-11-20T09:30" for 30 minutes
    And "Dr Paris" has a "NO_SHOW" "ONLINE" appointment at "2026-11-20T10:00" for 30 minutes
    And "Dr Paris" has a "CANCELLED" "ONLINE" appointment at "2026-11-20T10:30" for 30 minutes
    When the admin views the dashboard for the range "today"
    Then the utilisation is 50 %

  Scenario: Taux d'absence : `NO_SHOW` ÷ RDV non annulés. Part en ligne : RDV de source `ONLINE` ou `ROUND_ROBIN` ÷ RDV non annulés.
    Given "Dr Paris" has a "BOOKED" "ONLINE" appointment at "2026-11-20T09:00" for 30 minutes
    And "Dr Paris" has a "COMPLETED" "ROUND_ROBIN" appointment at "2026-11-20T09:30" for 30 minutes
    And "Dr Paris" has a "NO_SHOW" "STAFF" appointment at "2026-11-20T10:00" for 30 minutes
    And "Dr Paris" has a "BOOKED" "STAFF" appointment at "2026-11-20T10:30" for 30 minutes
    And "Dr Paris" has a "CANCELLED" "ONLINE" appointment at "2026-11-20T11:00" for 30 minutes
    When the admin views the dashboard for the range "today"
    Then the no-show rate is 25 %
    And the online share is 50 %

  Scenario: Taille de la liste d'attente : entrées `WAITING` ou `OFFERED`, quelle que soit la période.
    Given waitlist entries with the statuses "WAITING, WAITING, OFFERED, BOOKED, EXPIRED"
    When the admin views the dashboard for the range "today"
    Then the waitlist size is 3

  Scenario: Un ratio dont le dénominateur est nul affiche « n/a », jamais 0 %.
    When the admin views the dashboard for the range "7"
    Then the utilisation, no-show rate and online share are "n/a"

  Scenario: Règle §10 : seul l'admin consulte le tableau de bord
    When the patient views the dashboard for the range "7"
    Then the dashboard is forbidden
