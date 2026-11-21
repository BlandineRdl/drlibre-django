Feature: Un créneau annulé est proposé au patient en attente le plus ancien
  En tant que patient inscrit sur la liste d'attente
  Je veux qu'on me propose le créneau d'un RDV annulé qui me correspond
  Afin que j'obtienne un RDV plus tôt

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And the patient has a "BOOKED" appointment with "A" at "2026-11-23 09:00" in room "R1"
    And an active patient "lea@example.org"
    And an active patient "tom@example.org"

  Scenario: À l'annulation d'un RDV, les entrées candidates sont `WAITING`, du même type, sans praticien préféré ou avec le praticien libéré, et leur fenêtre contient le créneau libéré. (avec le praticien libéré)
    Given "lea@example.org" waits preferring "A" from "2026-11-23 09:00" to "2026-11-23 09:30" since "2026-11-01 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then the entry of "lea@example.org" is offered the appointment the patient cancelled

  Scenario Outline: À l'annulation d'un RDV, les entrées candidates sont `WAITING`, du même type, sans praticien préféré ou avec le praticien libéré, et leur fenêtre contient le créneau libéré. (<case>)
    Given "lea@example.org" waits <unfit> since "2026-11-01 08:00"
    And "tom@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-02 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then the entry of "tom@example.org" is offered the appointment the patient cancelled
    And the entry of "lea@example.org" is unchanged

    Examples:
      | case                         | unfit                                                                         |
      | autre type                   | for another type from "2026-11-22 00:00" to "2026-11-24 00:00"                |
      | autre praticien préféré      | preferring "B" from "2026-11-22 00:00" to "2026-11-24 00:00"                  |
      | fenêtre finissant trop tôt   | from "2026-11-22 00:00" to "2026-11-23 09:29"                                 |
      | fenêtre commençant trop tard | from "2026-11-23 09:01" to "2026-11-24 00:00"                                 |
      | entrée expirée               | from "2026-11-22 00:00" to "2026-11-24 00:00" already "EXPIRED"               |

  Scenario: À l'annulation d'un RDV, les entrées candidates sont `WAITING`, du même type, sans praticien préféré ou avec le praticien libéré, et leur fenêtre contient le créneau libéré. (pas celles du patient qui annule)
    Given "patient@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    And "tom@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-02 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then the entry of "tom@example.org" is offered the appointment the patient cancelled
    And the entry of "patient@example.org" is unchanged

  Scenario: La plus ancienne gagne (à égalité, le plus petit id) : elle passe en `OFFERED`, liée au RDV annulé. Une seule entrée reçoit l'offre ; sans candidate, rien ne change. (la plus ancienne)
    Given "tom@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-02 08:00"
    And "lea@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then the entry of "lea@example.org" is offered the appointment the patient cancelled
    And the entry of "tom@example.org" is unchanged

  Scenario: La plus ancienne gagne (à égalité, le plus petit id) : elle passe en `OFFERED`, liée au RDV annulé. Une seule entrée reçoit l'offre ; sans candidate, rien ne change. (à égalité)
    Given "lea@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    And "tom@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then only the entry with the lowest id is offered the appointment the patient cancelled

  Scenario: La plus ancienne gagne (à égalité, le plus petit id) : elle passe en `OFFERED`, liée au RDV annulé. Une seule entrée reçoit l'offre ; sans candidate, rien ne change. (sans candidate)
    Given "lea@example.org" waits preferring "B" from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then no entry was offered

  Scenario: L'entrée offerte montre au patient l'heure proposée et un bouton « Accepter ».
    Given "lea@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then the own list of "lea@example.org" shows the offer at "2026-11-23 09:00" that can be accepted

  Scenario: L'offre ne réserve rien : le créneau reste libre pour toute autre réservation.
    Given "lea@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    And "A" is free at "2026-11-23 09:00"
    When the patient cancels it giving the reason "Empêchement"
    And another patient books "A" at "2026-11-23 09:00"
    Then the other patient's booking is placed
    And the entry of "lea@example.org" is offered the appointment the patient cancelled

  Scenario: La notification « Créneau proposé » ne porte que l'heure ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion.
    Given "lea@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then "lea@example.org" has one "Créneau proposé" notification at "23/11/2026 à 10:00", linking no appointment
    And one email "Un créneau vous est proposé" to "lea@example.org" names the time "2026-11-23 09:00", hospital and provider "A", without a reason, linking only to the sign-in page

  Scenario: L'offre laisse une entrée d'audit sans donnée personnelle.
    Given "lea@example.org" waits from "2026-11-22 00:00" to "2026-11-24 00:00" since "2026-11-01 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then the audit holds "booking.waitlist_offered" by nobody with ids only

  Scenario: Règle §5.8 : une annulation refusée ne propose aucun créneau
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-21 09:00" in room "R1"
    And "lea@example.org" waits from "2026-11-21 00:00" to "2026-11-22 00:00" since "2026-11-01 08:00"
    When the patient cancels it giving the reason "Empêchement"
    Then the booking is refused as "rule_violation"
    And no entry was offered
