Feature: Un client agit avec le jeton d'un utilisateur et exactement ses droits
  En tant que client API
  Je veux m'authentifier avec le jeton bearer d'un utilisateur
  Afin d'accéder à ce que cet utilisateur voit à l'écran, ni plus ni moins

  Scenario: Une commande d'administration émet un jeton pour un utilisateur ; la seed fournit un jeton de démo par rôle (admin, praticien, patient) (commande)
    Given an active "PATIENT" "lea@example.org"
    When the administration command issues a token for "lea@example.org"
    Then the command prints the token once
    And only the hash of the token is stored for "lea@example.org"
    And the audit log holds "identity.api_token_issued" without personal data

  @integration @django_db
  Scenario: Une commande d'administration émet un jeton pour un utilisateur ; la seed fournit un jeton de démo par rôle (admin, praticien, patient) (seed)
    When the demo seed runs twice
    Then the demo tokens "demo-admin-token", "demo-clinician-token" and "demo-patient-token" are stored once each
    And each demo token authenticates a user of its role

  Scenario Outline: Un jeton invalide renvoie `unauthenticated` (401) ; un jeton valide donne exactement les droits de son utilisateur (<case>)
    Given an active "PATIENT" "lea@example.org" holding a token
    And <change>
    When the client calls "GET" "/fhir/metadata" with that token
    Then the answer is 401 with an OperationOutcome "login" and the code "unauthenticated"

    Examples:
      | case                  | change                                              |
      | jeton inconnu         | the client sends another token instead              |
      | jeton expiré          | the token has expired                               |
      | jeton révoqué         | the command revokes the tokens of "lea@example.org" |
      | utilisateur désactivé | "lea@example.org" is deactivated                    |

  Scenario Outline: Un jeton invalide renvoie `unauthenticated` (401) ; un jeton valide donne exactement les droits de son utilisateur (droits : <case>)
    Given an active "<role>" "user@example.org" holding a token
    When the client calls "POST" "/api/v1/jobs/reminders" with that token
    Then the answer is <status>

    Examples:
      | case                                 | role    | status |
      | l'admin lance les rappels            | ADMIN   | 200    |
      | le patient ne lance pas les rappels  | PATIENT | 403    |

  Scenario: Un jeton invalide renvoie `unauthenticated` (401) ; un jeton valide donne exactement les droits de son utilisateur (mot de passe à changer d'abord)
    Given an active "CLINICIAN" "dr@example.org" holding a token
    And "dr@example.org" must change their password
    When the client calls "GET" "/fhir/metadata" with that token
    Then the answer is 403 with an OperationOutcome "forbidden" and the code "forbidden"

  @integration @django_db
  Scenario: Avec un jeton du personnel, `Practitioner` et `PractitionerRole` renvoient tous les champs, y compris email et téléphone, et `Slot` accepte les statuts `busy`, `busy-tentative` et `busy-unavailable` ; seul l'admin voit les `Practitioner` admins. (Practitioner et PractitionerRole)
    Given a reference directory of active and closed hospitals, their departments, rooms, types, specialties and clinicians
    When a client without a token reads "/fhir/PractitionerRole/$profile"
    Then the role hides the round robin weight, the reason and the types booked offline
    When the client with the "clinician" token reads "/fhir/Practitioner/$clinician"
    Then the practitioner shows the email and phone of "clinician"
    When the client with the "clinician" token reads "/fhir/PractitionerRole/$profile"
    Then the role shows the round robin weight 3 and the reason "Congés"
    When the client with the "clinician" token reads "/fhir/Practitioner/$former"
    Then the answer is a FHIR "Practitioner" with the id of "former"

  @integration @django_db
  Scenario: Avec un jeton du personnel, `Practitioner` et `PractitionerRole` renvoient tous les champs, y compris email et téléphone, et `Slot` accepte les statuts `busy`, `busy-tentative` et `busy-unavailable` ; seul l'admin voit les `Practitioner` admins. (Practitioner admins)
    Given a reference directory of active and closed hospitals, their departments, rooms, types, specialties and clinicians
    When the client with the "clinician" token reads "/fhir/Practitioner/$admin"
    Then the client is refused with 404 and the code "not_found"
    When the client with the "admin" token reads "/fhir/Practitioner/$admin"
    Then the answer is a FHIR "Practitioner" with the id of "admin"
    When the client with the "admin" token reads "/fhir/PractitionerRole/$admin"
    Then the role is coded "admin" for "Practitioner/$admin"
