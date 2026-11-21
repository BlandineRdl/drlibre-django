Feature: Une entrée dont la fenêtre est passée expire
  En tant que patient inscrit sur la liste d'attente
  Je veux que mon entrée expire quand sa fenêtre est passée
  Afin que la liste ne garde que des attentes encore utiles

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And a signed-in patient
    And an active patient "lea@example.org"
    And an active patient "tom@example.org"

  Scenario: Exécuté sur planning, sans action d'un admin, le job d'expiration fait passer en `EXPIRED` chaque entrée `WAITING` dont la date limite est passée. (date limite passée)
    Given "lea@example.org" waits from "2026-11-10 00:00" to "2026-11-20 10:00" since "2026-11-01 08:00"
    And "tom@example.org" waits from "2026-11-10 00:00" to "2026-11-20 10:01" since "2026-11-01 08:00"
    When the waitlist expiry job runs
    Then the entry of "lea@example.org" is now "EXPIRED"
    And the entry of "tom@example.org" is unchanged
    And the job changed 1 entries

  Scenario: Exécuté sur planning, sans action d'un admin, le job d'expiration fait passer en `EXPIRED` chaque entrée `WAITING` dont la date limite est passée. (deuxième passage)
    Given "lea@example.org" waits from "2026-11-10 00:00" to "2026-11-20 10:00" since "2026-11-01 08:00"
    When the waitlist expiry job runs
    And the waitlist expiry job runs
    Then the entry of "lea@example.org" is now "EXPIRED"
    And the job changed 1 entries, then 0
    And the audit holds "booking.waitlist_expired" by nobody with the status "EXPIRED"

  Scenario: Une entrée `EXPIRED` ne reçoit plus d'offre. (à l'annulation)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-23 09:00" in room "R1"
    And "lea@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" already "EXPIRED" since "2026-11-01 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then no entry was offered

  Scenario: Une entrée `EXPIRED` ne reçoit plus d'offre. (offre manuelle)
    Given a signed-in admin
    And a cancelled appointment with "A" at "2026-11-23 09:00"
    And "A" is free at "2026-11-23 09:00"
    And "lea@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" already "EXPIRED" since "2026-11-01 08:00"
    When the admin offers a slot to the entry of "lea@example.org"
    Then the offer is refused as "invalid_transition"
    And no entry was offered

  Scenario: L'expiration laisse une entrée d'audit sans donnée personnelle.
    Given "lea@example.org" waits from "2026-11-10 00:00" to "2026-11-20 10:00" since "2026-11-01 08:00"
    When the waitlist expiry job runs
    Then the audit holds "booking.waitlist_expired" by nobody with the status "EXPIRED"
