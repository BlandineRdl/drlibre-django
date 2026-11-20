Feature: Chaque rôle n'accède qu'à son espace
  En tant qu'admin
  Je veux que chaque page vérifie qui la demande
  Afin que personne n'agisse hors de ses droits

  Background:
    Given an active CLINICIAN "clinician@example.org" with password "clinic-password-1"
    And an active CLINICIAN "other@example.org" with password "other-password-1"
    And an active ADMIN "admin@example.org" with password "admin-password-1"

  Scenario Outline: Sans session, toute page non publique renvoie vers la connexion (<page>)
    Then the page "<page>" sends them to "/sign-in?next=<next>"

    Examples:
      | page              | next                |
      | /console/         | %2Fconsole%2F       |
      | /workspace/       | %2Fworkspace%2F     |
      | /portal/          | %2Fportal%2F        |
      | /account/password | %2Faccount%2Fpassword |

  Scenario Outline: Un utilisateur connecté qui ouvre l'espace d'un autre rôle voit une page « forbidden » (<page>)
    When "clinician@example.org" signs in on the sign-in page with "clinic-password-1"
    Then the page "<page>" is forbidden

    Examples:
      | page                |
      | /console/           |
      | /console/hospitals/ |
      | /portal/            |

  Scenario: Un enregistrement absent donne not_found
    When "clinician@example.org" opens an absent record
    Then access is refused as "not_found"

  Scenario: Un enregistrement existant mais appartenant à un autre donne forbidden
    When "clinician@example.org" opens a record owned by "other@example.org"
    Then access is refused as "forbidden"

  Scenario: Un enregistrement appartenant à l'utilisateur lui est rendu
    When "clinician@example.org" opens a record owned by "clinician@example.org"
    Then the record is returned

  Scenario: Un admin, global, atteint les enregistrements de tous
    When "admin@example.org" opens a record owned by "other@example.org"
    Then the record is returned

  Scenario Outline: Les requêtes d'écriture venant d'une autre origine sont refusées (<path>)
    When a POST to "<path>" arrives from origin "https://evil.example"
    Then the response is 403 "forbidden"
    And nothing is audited

    Examples:
      | path                   |
      | /api/v1/auth/login     |
      | /sign-in               |
      | /console/hospitals/new |
