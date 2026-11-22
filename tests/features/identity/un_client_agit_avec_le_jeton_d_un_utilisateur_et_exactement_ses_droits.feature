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
  Scenario: Avec un jeton du personnel, `Practitioner` et `PractitionerRole` renvoient tous les champs, y compris email et téléphone, et `Slot` accepte les statuts `busy`, `busy-tentative` et `busy-unavailable` ; seul l'admin voit les `Practitioner` admins. (motif d'absence : le praticien concerné et l'admin seulement)
    Given a reference directory of active and closed hospitals, their departments, rooms, types, specialties and clinicians
    When the client with the "admin" token reads "/fhir/PractitionerRole/$profile"
    Then the role shows the round robin weight 3 and the reason "Congés"
    When the client with a colleague clinician's token reads "/fhir/PractitionerRole/$profile"
    Then the role shows the round robin weight 3 without the reason

  @integration @django_db
  Scenario: Avec un jeton du personnel, `Practitioner` et `PractitionerRole` renvoient tous les champs, y compris email et téléphone, et `Slot` accepte les statuts `busy`, `busy-tentative` et `busy-unavailable` ; seul l'admin voit les `Practitioner` admins. (Practitioner admins)
    Given a reference directory of active and closed hospitals, their departments, rooms, types, specialties and clinicians
    When the client with the "clinician" token reads "/fhir/Practitioner/$admin"
    Then the client is refused with 404 and the code "not_found"
    When the client with the "admin" token reads "/fhir/Practitioner/$admin"
    Then the answer is a FHIR "Practitioner" with the id of "admin"
    When the client with the "admin" token reads "/fhir/PractitionerRole/$admin"
    Then the role is coded "admin" for "Practitioner/$admin"

  @integration @django_db
  Scenario: Avec un jeton du personnel, `Practitioner` et `PractitionerRole` renvoient tous les champs, y compris email et téléphone, et `Slot` accepte les statuts `busy`, `busy-tentative` et `busy-unavailable` ; seul l'admin voit les `Practitioner` admins. (Slot)
    Given a reference directory of active and closed hospitals, their departments, rooms, types, specialties and clinicians
    Given on "2026-11-20" the clinician is held at "09:00", booked at "10:00" and off at "11:00" on "2026-11-23"
    When the client with the "clinician" token searches "/fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-11-24T00:00:00%2B01:00&status=busy,busy-tentative,busy-unavailable"
    Then the FHIR slots are "09:00 busy-tentative, 09:15 busy-tentative, 09:45 busy, 10:00 busy, 10:15 busy, 10:45 busy-unavailable, 11:00 busy-unavailable, 11:15 busy-unavailable"
    When the client with the "admin" token searches "/fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-11-24T00:00:00%2B01:00&status=free,busy"
    Then the FHIR slots are "09:30 free, 09:45 busy, 10:00 busy, 10:15 busy, 10:30 free, 11:30 free"
    When a client without a token searches "/fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-11-24T00:00:00%2B01:00&status=busy"
    Then the client is refused with 403 and the code "forbidden"
    When the client with a patient token searches "/fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-11-24T00:00:00%2B01:00&status=busy"
    Then the client is refused with 403 and the code "forbidden"

  @integration @django_db
  Scenario: Avec un jeton du personnel, `Practitioner` et `PractitionerRole` renvoient tous les champs, y compris email et téléphone, et `Slot` accepte les statuts `busy`, `busy-tentative` et `busy-unavailable` ; seul l'admin voit les `Practitioner` admins. (Slot dans une fenêtre déjà passée)
    Given a reference directory of active and closed hospitals, their departments, rooms, types, specialties and clinicians
    Given on "2026-11-20" the clinician is held at "09:00", booked at "10:00" and off at "11:00" on "2026-11-23"
    When the client with the "clinician" token searches "/fhir/Slot?service-type=$online&start=ge2026-11-16T00:00:00%2B01:00&start=lt2026-11-20T11:00:00%2B01:00&status=busy,busy-tentative,busy-unavailable"
    Then the FHIR slots are ""

  @integration @django_db
  Scenario: `Patient` (nom, date de naissance, email, téléphone, actif) est lisible par le patient lui-même, par un praticien pour ses propres patients, et par l'admin ; une autre fiche existante donne `forbidden`.
    Given two patients, a clinician who has seen the first one and an admin
    When "first" reads the patient "first"
    Then the patient "first" is shown with their name, birth date, email, phone and status
    When "clinician" reads the patient "first"
    Then the patient "first" is shown with their name, birth date, email, phone and status
    When "admin" reads the patient "second"
    Then the patient "second" is shown with their name, birth date, email, phone and status
    When "first" reads the patient "second"
    Then the client is refused with 403 and the code "forbidden"
    When "clinician" reads the patient "second"
    Then the client is refused with 403 and the code "forbidden"
    When "first" reads the patient "absent"
    Then the client is refused with 404 and the code "not_found"
    When "nobody" reads the patient "first"
    Then the client is refused with 401 and the code "unauthenticated"

  @integration @django_db
  Scenario: Les recherches `Patient` acceptent `name`, `email`, `phone` et `birthdate`, limitées à ce que l'utilisateur peut voir.
    Given two patients, a clinician who has seen the first one and an admin
    When "admin" searches the patients with "_sort=-name"
    Then the FHIR patients found are "second, first"
    When "admin" searches the patients with "name=durand"
    Then the FHIR patients found are "first"
    When "admin" searches the patients with "email=$second_email"
    Then the FHIR patients found are "second"
    When "admin" searches the patients with "phone=0611111111"
    Then the FHIR patients found are "first"
    When "admin" searches the patients with "birthdate=1990-05-01"
    Then the FHIR patients found are "second"
    When "clinician" searches the patients with "_sort=name"
    Then the FHIR patients found are "first"
    When "first" searches the patients with "name=Bruno"
    Then no FHIR patient is found
    When "first" searches the patients with "birthdate=ge1990-05-01"
    Then the client is refused with 400 and the code "invalid_input"

  @integration @django_db
  Scenario: Le patient met à jour son propre téléphone et sa date de naissance ; une mise à jour avec un `If-Match` périmé échoue en 412.
    Given two patients, a clinician who has seen the first one and an admin
    When "first" updates the patient "first" with phone "0633333333" and birth date "1985-02-03" at the current version
    Then the update answers 200 with a new version
    And the patient "first" has phone "0633333333" and birth date "1985-02-03"
    When "first" updates the patient "first" with phone "0644444444" and birth date "1985-02-03" at the previous version
    Then the client is refused with 412 and the code "conflict"
    And the patient "first" has phone "0633333333" and birth date "1985-02-03"

  @integration @django_db
  Scenario Outline: Le patient met à jour son propre téléphone et sa date de naissance ; une mise à jour avec un `If-Match` périmé échoue en 412. (<case>)
    Given two patients, a clinician who has seen the first one and an admin
    When "<who>" changes the <field> of the patient "first" to "<value>"
    Then the client is refused with <status> and the code "<code>"
    And the patient "first" has phone "0611111111" and birth date "1980-03-04"

    Examples:
      | case                              | who       | field     | value             | status | code          |
      | rien d'autre : son nom            | first     | name      | Anne Autre        | 400    | invalid_input |
      | rien d'autre : son email          | first     | email     | autre@example.org | 400    | invalid_input |
      | pas la fiche d'un autre           | second    | birthDate | 1970-01-01        | 403    | forbidden     |
      | pas le praticien                  | clinician | birthDate | 1970-01-01        | 403    | forbidden     |

  @integration @django_db
  Scenario: Chaque écriture laisse la même entrée d'audit que l'écran correspondant. (Patient et profil)
    Given two patients, a clinician who has seen the first one and an admin
    When "first" updates the patient "first" with phone "0633333333" and birth date "1985-02-03" at the current version
    And "second" saves phone "0633333333" and birth date "1985-02-03" on the profile screen
    Then the "first" and "second" entries "user.profile_updated" are alike but for the actor
