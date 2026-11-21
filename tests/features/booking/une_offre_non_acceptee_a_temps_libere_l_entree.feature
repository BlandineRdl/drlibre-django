Feature: Une offre non acceptée à temps libère l'entrée
  En tant que patient inscrit sur la liste d'attente
  Je veux que mon entrée revienne en attente si je n'ai pas accepté le créneau avant qu'il commence
  Afin qu'un autre créneau puisse m'être proposé

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And a signed-in patient
    And an active patient "lea@example.org"

  Scenario Outline: Quand le créneau d'une entrée `OFFERED` commence sans acceptation, le job d'expiration la fait repasser en `WAITING`, ou en `EXPIRED` si sa date limite est passée. (<case>)
    Given "lea@example.org" is offered the cancelled appointment with "A" at "<start>", waiting until "<end>"
    When the waitlist expiry job runs
    Then the entry of "lea@example.org" is now "<status>" with no offer
    And the job changed 1 entries

    Examples:
      | case                     | start            | end              | status  |
      | fenêtre encore ouverte   | 2026-11-20 10:00 | 2026-11-25 00:00 | WAITING |
      | date limite passée       | 2026-11-20 09:00 | 2026-11-20 09:30 | EXPIRED |

  Scenario: Quand le créneau d'une entrée `OFFERED` commence sans acceptation, le job d'expiration la fait repasser en `WAITING`, ou en `EXPIRED` si sa date limite est passée. (créneau pas encore commencé)
    Given "lea@example.org" is offered the cancelled appointment with "A" at "2026-11-20 10:01"
    When the waitlist expiry job runs
    Then the entry of "lea@example.org" is now "OFFERED"
    And the job changed 0 entries

  Scenario: Revenue en `WAITING`, l'entrée peut recevoir une nouvelle offre.
    Given "lea@example.org" is offered the cancelled appointment with "A" at "2026-11-20 09:30", waiting until "2026-11-25 00:00"
    And the patient has a "BOOKED" appointment with "A" at "2026-11-23 09:00" in room "R1"
    When the waitlist expiry job runs
    And the patient cancels it giving the reason "Empêchement"
    Then the entry of "lea@example.org" is offered the appointment the patient cancelled

  Scenario: Le changement laisse une entrée d'audit sans donnée personnelle.
    Given "lea@example.org" is offered the cancelled appointment with "A" at "2026-11-20 09:30", waiting until "2026-11-25 00:00"
    When the waitlist expiry job runs
    Then the audit holds "booking.waitlist_offer_lapsed" by nobody with the status "WAITING"
