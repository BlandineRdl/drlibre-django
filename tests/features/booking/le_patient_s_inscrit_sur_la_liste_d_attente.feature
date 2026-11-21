Feature: Le patient s'inscrit sur la liste d'attente
  En tant que patient connecté, avec ou sans mot de passe
  Je veux m'inscrire en attente d'un créneau pour un type de RDV
  Afin qu'un créneau libéré puisse m'être proposé

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And an active clinician "A" in that department
    And a signed-in patient

  Scenario: Le formulaire demande un type de RDV, un praticien préféré facultatif et une fenêtre de dates ; l'entrée est créée en `WAITING` pour le patient de la session, qui ne peut nommer personne d'autre. (avec un praticien préféré)
    When the patient joins the waitlist with "A" from "2026-11-23" to "2026-11-27"
    Then the waitlist holds one "WAITING" entry for the signed-in patient with "A"
    And the entry waits from "2026-11-23 00:00" to "2026-11-28 00:00" in "Europe/Paris"

  Scenario: Le formulaire demande un type de RDV, un praticien préféré facultatif et une fenêtre de dates ; l'entrée est créée en `WAITING` pour le patient de la session, qui ne peut nommer personne d'autre. (sans praticien, dans le fuseau de l'hôpital)
    Given the appointment type is in the time zone "America/Martinique"
    When the patient joins the waitlist from "2026-11-20" to "2026-11-20"
    Then the waitlist holds one "WAITING" entry for the signed-in patient with no clinician
    And the entry waits from "2026-11-20 00:00" to "2026-11-21 00:00" in "America/Martinique"

  Scenario: Le formulaire demande un type de RDV, un praticien préféré facultatif et une fenêtre de dates ; l'entrée est créée en `WAITING` pour le patient de la session, qui ne peut nommer personne d'autre. (nommer un autre patient)
    Given an active patient "other@example.org"
    When the patient joins the waitlist naming "other@example.org" from "2026-11-23" to "2026-11-27"
    Then the join is refused as "forbidden"
    And nothing was written to the waitlist

  Scenario Outline: Un type ou un praticien préféré inconnu ou inactif donne `not_found`. (<case>)
    Given the waitlist choice "<choice>" is unusable
    When the patient joins the waitlist with "A" from "2026-11-23" to "2026-11-27"
    Then the join is refused as "not_found"
    And nothing was written to the waitlist

    Examples:
      | case                           | choice                        |
      | type inconnu                   | unknown type                  |
      | type inactif                   | inactive type                 |
      | praticien inconnu              | unknown clinician             |
      | praticien inactif              | inactive clinician            |
      | praticien d'un autre service   | clinician of another department |

  Scenario: Le patient voit la liste de ses entrées avec leur statut.
    Given an active patient "other@example.org"
    And "other@example.org" waits on the waitlist
    When the patient joins the waitlist with "A" from "2026-11-23" to "2026-11-27"
    And the patient joins the waitlist from "2026-11-24" to "2026-11-30"
    Then the patient's own list shows "WAITING, WAITING", newest first

  Scenario: L'inscription laisse une entrée d'audit sans donnée personnelle.
    When the patient joins the waitlist with "A" from "2026-11-23" to "2026-11-27"
    Then the audit holds "booking.waitlist_joined" by the signed-in patient with ids only

  Scenario: Règle §5.3 : un patient ne s'inscrit que pour un type réservable en ligne
    Given the appointment type is not bookable online
    When the patient joins the waitlist with "A" from "2026-11-23" to "2026-11-27"
    Then the join is refused as "rule_violation"
    And the refusal names the rules "type_not_bookable_online"
    And nothing was written to the waitlist

  Scenario Outline: Règle §5.8 : la fenêtre finit après son début et au plus tôt aujourd'hui (<case>)
    When the patient joins the waitlist from "<from>" to "<to>"
    Then the join is refused as "invalid_input"
    And the refusal names the field "to_date"
    And nothing was written to the waitlist

    Examples:
      | case                  | from       | to         |
      | fin avant le début    | 2026-11-25 | 2026-11-24 |
      | fin déjà passée       | 2026-11-10 | 2026-11-19 |

  Scenario: Règle §5.8 : seul un patient s'inscrit lui-même ; un praticien est refusé
    Given a signed-in clinician
    When the clinician joins the waitlist from "2026-11-23" to "2026-11-27"
    Then the join is refused as "forbidden"
    And nothing was written to the waitlist
