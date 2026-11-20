Feature: Health check
  Operators and the container runtime learn whether the application can serve requests.

  Scenario: The database answers
    Given the clock reads "2026-11-20T10:00:00+00:00"
    And the database is up
    When the health is checked
    Then the status is "ok"
    And the database is reported "up"
    And the report is dated "2026-11-20T10:00:00+00:00"

  Scenario: The database does not answer
    Given the clock reads "2026-11-20T10:00:00+00:00"
    And the database is down
    When the health is checked
    Then the status is "degraded"
    And the database is reported "down"
