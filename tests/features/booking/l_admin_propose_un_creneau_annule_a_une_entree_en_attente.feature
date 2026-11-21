Feature: L'admin propose un créneau annulé à une entrée en attente
  En tant qu'admin
  Je veux proposer à une entrée en attente le premier créneau annulé qui lui convient
  Afin qu'un créneau libéré trouve preneur même sans offre automatique

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And an active clinician "A" in that department
    And an active clinician "B" in that department
    And a signed-in admin
    And an active patient "lea@example.org"
    And an active patient "tom@example.org"
    And "lea@example.org" waits from "2026-11-22 00:00" to "2026-11-30 00:00" since "2026-11-01 08:00"
    And a cancelled appointment with "A" at "2026-11-24 09:00"
    And a cancelled appointment with "B" at "2026-11-25 09:00"
    And "A" is free at "2026-11-24 09:00"
    And "B" is free at "2026-11-25 09:00"

  Scenario: Sur une entrée `WAITING`, l'offre manuelle retient le premier créneau annulé à venir du même type dans sa fenêtre, si son praticien est encore libre à cette heure et qu'aucune autre entrée ne détient cette offre. (le premier qui convient)
    Given a cancelled appointment with "A" at "2026-11-20 09:00"
    And a cancelled appointment with "A" at "2026-11-21 09:00"
    And a cancelled appointment of another type with "A" at "2026-11-23 09:00"
    When the admin offers a slot to the entry of "lea@example.org"
    Then the entry of "lea@example.org" is offered the cancelled appointment at "2026-11-24 09:00"

  Scenario: Sur une entrée `WAITING`, l'offre manuelle retient le premier créneau annulé à venir du même type dans sa fenêtre, si son praticien est encore libre à cette heure et qu'aucune autre entrée ne détient cette offre. (praticien plus libre)
    Given "A" is no longer free at "2026-11-24 09:00"
    When the admin offers a slot to the entry of "lea@example.org"
    Then the entry of "lea@example.org" is offered the cancelled appointment at "2026-11-25 09:00"

  Scenario: Sur une entrée `WAITING`, l'offre manuelle retient le premier créneau annulé à venir du même type dans sa fenêtre, si son praticien est encore libre à cette heure et qu'aucune autre entrée ne détient cette offre. (déjà proposé à une autre entrée)
    Given "tom@example.org" holds the offer of the cancelled appointment at "2026-11-24 09:00"
    When the admin offers a slot to the entry of "lea@example.org"
    Then the entry of "lea@example.org" is offered the cancelled appointment at "2026-11-25 09:00"

  Scenario: Sur une entrée `WAITING`, l'offre manuelle retient le premier créneau annulé à venir du même type dans sa fenêtre, si son praticien est encore libre à cette heure et qu'aucune autre entrée ne détient cette offre. (praticien préféré)
    Given "tom@example.org" waits preferring "B" from "2026-11-22 00:00" to "2026-11-30 00:00" since "2026-11-02 08:00"
    When the admin offers a slot to the entry of "tom@example.org"
    Then the entry of "tom@example.org" is offered the cancelled appointment at "2026-11-25 09:00"

  Scenario: Sur une entrée `WAITING`, l'offre manuelle retient le premier créneau annulé à venir du même type dans sa fenêtre, si son praticien est encore libre à cette heure et qu'aucune autre entrée ne détient cette offre. (aucun créneau ne convient)
    Given "tom@example.org" waits from "2026-11-26 00:00" to "2026-11-30 00:00" since "2026-11-02 08:00"
    When the admin offers a slot to the entry of "tom@example.org"
    Then the offer is refused as "not_found"
    And no entry was offered

  Scenario: L'entrée passe en `OFFERED`, liée à ce RDV annulé, et le patient la voit avec l'heure proposée et le bouton « Accepter ».
    When the admin offers a slot to the entry of "lea@example.org"
    Then the entry of "lea@example.org" is offered the cancelled appointment at "2026-11-24 09:00"
    And the own list of "lea@example.org" shows the offer at "2026-11-24 09:00" that can be accepted

  Scenario: La notification « Créneau proposé » ne porte que l'heure ; l'email part après sa validation, avec l'heure, l'hôpital et le praticien, sans motif, et ne renvoie qu'à la page de connexion.
    When the admin offers a slot to the entry of "lea@example.org"
    Then "lea@example.org" has one "Créneau proposé" notification at "24/11/2026 à 10:00", linking no appointment
    And one email "Un créneau vous est proposé" to "lea@example.org" names the time "2026-11-24 09:00", hospital and provider "A", without a reason, linking only to the sign-in page

  Scenario: L'offre laisse une entrée d'audit sans donnée personnelle.
    When the admin offers a slot to the entry of "lea@example.org"
    Then the audit holds "booking.waitlist_offered" by the admin with ids only

  Scenario: Règle §5.8 : seule une entrée en attente reçoit une offre manuelle
    Given the entry of "lea@example.org" is "EXPIRED"
    When the admin offers a slot to the entry of "lea@example.org"
    Then the offer is refused as "invalid_transition"
    And the refusal names the status "EXPIRED"
    And no entry was offered

  Scenario: Règle §5.8 : seul un admin propose un créneau
    Given a signed-in clinician
    When the clinician offers a slot to the entry of "lea@example.org"
    Then the offer is refused as "forbidden"
    And no entry was offered
