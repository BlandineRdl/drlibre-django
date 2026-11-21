Feature: L'admin inscrit un patient sur la liste d'attente
  En tant qu'admin
  Je veux inscrire un patient sur la liste d'attente
  Afin qu'un patient qui ne le fait pas lui-même puisse recevoir une offre

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And an active clinician "A" in that department
    And a signed-in admin
    And an active patient "lea@example.org"

  Scenario: L'admin choisit un patient actif, un type actif, un praticien préféré actif facultatif et une fenêtre de dates ; l'entrée est créée en `WAITING` et apparaît dans la liste. (avec un praticien préféré)
    When the admin adds "LEA@example.org" to the waitlist with "A" from "2026-11-23" to "2026-11-27"
    Then the waitlist holds one "WAITING" entry for "lea@example.org" with "A"
    And the admin list shows that entry

  Scenario: L'admin choisit un patient actif, un type actif, un praticien préféré actif facultatif et une fenêtre de dates ; l'entrée est créée en `WAITING` et apparaît dans la liste. (type non réservable en ligne)
    Given the appointment type is not bookable online
    When the admin adds "lea@example.org" to the waitlist from "2026-11-23" to "2026-11-27"
    Then the waitlist holds one "WAITING" entry for "lea@example.org" with no clinician

  Scenario Outline: Un patient, un type ou un praticien inconnu ou inactif donne `not_found`. (<case>)
    Given the waitlist choice "<choice>" is unusable
    When the admin adds "lea@example.org" to the waitlist with "A" from "2026-11-23" to "2026-11-27"
    Then the join is refused as "not_found"
    And nothing was written to the waitlist

    Examples:
      | case              | choice             |
      | patient inconnu   | unknown patient    |
      | patient inactif   | inactive patient   |
      | type inconnu      | unknown type       |
      | type inactif      | inactive type      |
      | praticien inconnu | unknown clinician  |
      | praticien inactif | inactive clinician |

  Scenario: L'inscription laisse une entrée d'audit sans donnée personnelle.
    When the admin adds "lea@example.org" to the waitlist with "A" from "2026-11-23" to "2026-11-27"
    Then the audit holds "booking.waitlist_joined" by the admin with ids only

  Scenario: `POST /waitlist` permet à l'admin de nommer le patient. (patient nommé)
    When the admin posts the waitlist join of "lea@example.org" from "2026-11-23" to "2026-11-27"
    Then the API answers 201 with a "WAITING" entry for "lea@example.org"

  Scenario: `POST /waitlist` permet à l'admin de nommer le patient. (patient inconnu)
    When the admin posts the waitlist join of "nobody@example.org" from "2026-11-23" to "2026-11-27"
    Then the API refuses with 404 "not_found"
    And nothing was written to the waitlist
