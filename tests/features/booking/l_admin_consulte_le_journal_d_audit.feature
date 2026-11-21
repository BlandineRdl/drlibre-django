Feature: L'admin consulte le journal d'audit
  En tant qu'admin
  Je veux parcourir le journal d'audit
  Afin que je retrouve qui a fait quoi, et sur quelle requête

  Background:
    Given a signed-in admin
    And an active patient "lea@example.org"
    And these audit entries
      | at               | actor             | action                     | entity       | correlation |
      | 2026-11-18 09:00 | lea@example.org   | booking.appointment_booked | appointment  | req-1       |
      | 2026-11-19 09:00 |                   | identity.sign_in_failed    | session      | req-2       |
      | 2026-11-19 23:30 | admin@example.org | hospital.created           | hospital     | req-3       |
      | 2026-11-20 08:00 | lea@example.org   | booking.appointment_booked | appointment  | req-4       |
      | 2026-11-20 08:30 |                   | booking.hold_created       | booking_hold | req-5       |

  Scenario: Le journal est en lecture seule : aucune entrée ne peut être modifiée ni supprimée.
    Then the journal offers no way to change or delete an entry

  Scenario: Les entrées les plus récentes viennent en premier, 20 par page avec le nombre total. (première page)
    Given 21 more audit entries one minute apart from "2026-11-20 09:00"
    When the admin reads the journal with "page=1"
    Then the journal shows 20 entries, the newest first, out of 26

  Scenario: Les entrées les plus récentes viennent en premier, 20 par page avec le nombre total. (dernière page)
    Given 21 more audit entries one minute apart from "2026-11-20 09:00"
    When the admin reads the journal with "page=2"
    Then the journal shows the correlations "req-5, req-4, req-3, req-2, req-1" out of 26

  Scenario Outline: Les filtres portent sur l'acteur, le type d'entité et la période ; une valeur inutilisable dans l'adresse revient au défaut. (<case>)
    When the admin reads the journal with "<query>"
    Then the journal shows the correlations "<shown>" out of <total>

    Examples:
      | case                  | query                                  | shown                    | total |
      | acteur         | actor=lea@example.org                  | req-4, req-1                      | 2     |
      | acteur inconnu | actor=nobody@example.org               |                                   | 0     |
      | type d'entité  | entity_type=hospital                   | req-3                             | 1     |
      | période locale | start=2026-11-20&end=2026-11-20        | req-5, req-4, req-3               | 3     |
      | combinés       | actor=lea@example.org&start=2026-11-19 | req-4                             | 1     |
      | type inconnu   | entity_type=planet                     | req-5, req-4, req-3, req-2, req-1 | 5     |
      | date illisible | start=hier&end=2026-02-30              | req-5, req-4, req-3, req-2, req-1 | 5     |

  Scenario: Chaque entrée montre l'heure, l'acteur (vide pour un échec de connexion ou une étape avant vérification de l'email), l'action, l'entité et le correlation id.
    When the admin reads the journal with "entity_type=appointment"
    Then the entry "req-4" shows "2026-11-20 08:00", the actor "lea@example.org", the action "booking.appointment_booked" and the entity "appointment"

  Scenario: Chaque entrée montre l'heure, l'acteur (vide pour un échec de connexion ou une étape avant vérification de l'email), l'action, l'entité et le correlation id. (acteur vide)
    When the admin reads the journal with "page=1"
    Then the entries "req-5, req-2" show no actor

  Scenario: Règle §10 : seul l'admin consulte le journal
    Given a signed-in "CLINICIAN" user
    Then reading the journal is forbidden
