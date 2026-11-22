Feature: L'admin gère le référentiel en FHIR
  En tant que client API agissant pour un admin
  Je veux créer, modifier et supprimer hôpitaux, départements, salles, spécialités, types de RDV, utilisateurs et profils praticiens en FHIR
  Afin qu'un outil externe maintienne l'organisation sans passer par la console

  Background:
    Given a reference directory of active and closed hospitals, their departments, rooms, types, specialties and clinicians

  Scenario Outline: L'admin seul crée, modifie et supprime `Organization`, `Location`, `HealthcareService`, `CodeSystem`, `ValueSet`, `Practitioner` et `PractitionerRole` ; tout autre utilisateur reçoit `forbidden`. (<case>)
    When "admin" creates the "<sample>" in FHIR
    Then the client is answered 201 with the "<resource>" written
    When "admin" renames the written "<resource>" under its version
    Then the client is answered 200 with the "<resource>" renamed
    When "admin" deletes the written "<resource>"
    Then the client is answered 204 and the written "<resource>" is gone

    Examples:
      | case             | sample           | resource          |
      | hôpital          | hôpital          | Organization      |
      | département      | département      | Organization      |
      | salle            | salle            | Location          |
      | type de RDV      | type de RDV      | HealthcareService |
      | spécialité       | spécialité       | CodeSystem        |
      | jeu de valeurs de spécialité | jeu de valeurs de spécialité | ValueSet |
      | praticien        | praticien        | Practitioner      |
      | profil praticien | profil praticien | PractitionerRole  |

  Scenario Outline: L'admin seul crée, modifie et supprime `Organization`, `Location`, `HealthcareService`, `CodeSystem`, `ValueSet`, `Practitioner` et `PractitionerRole` ; tout autre utilisateur reçoit `forbidden`. (<case>, refusé)
    When "<who>" sends "<method>" to "<path>" with the "<sample>"
    Then the client is refused with 403 and the code "forbidden"
    And no audit entry was left

    Examples:
      | case                                  | who       | method | path                       | sample           |
      | un praticien crée un hôpital          | clinician | POST   | /fhir/Organization         | hôpital          |
      | un patient modifie une salle          | patient   | PUT    | /fhir/Location/$room       | salle            |
      | un praticien supprime un type de RDV  | clinician | DELETE | /fhir/HealthcareService/$online | type de RDV |
      | un patient crée une spécialité        | patient   | POST   | /fhir/CodeSystem           | spécialité       |
      | un praticien modifie un praticien     | clinician | PUT    | /fhir/Practitioner/$clinician | praticien     |
      | un patient supprime un profil         | patient   | DELETE | /fhir/PractitionerRole/$profile | profil praticien |
      | un praticien modifie un hôpital | clinician | PUT | /fhir/Organization/$lille | hôpital |
      | un patient supprime un département | patient | DELETE | /fhir/Organization/$cardiology | département |
      | un praticien crée une salle | clinician | POST | /fhir/Location | salle |
      | un patient supprime une salle | patient | DELETE | /fhir/Location/$room | salle |
      | un patient crée un type de RDV | patient | POST | /fhir/HealthcareService | type de RDV |
      | un praticien modifie un type de RDV | clinician | PUT | /fhir/HealthcareService/$online | type de RDV |
      | un praticien modifie une spécialité | clinician | PUT | /fhir/CodeSystem/$specialty | spécialité |
      | un patient supprime une spécialité | patient | DELETE | /fhir/CodeSystem/$specialty | spécialité |
      | un patient crée un praticien | patient | POST | /fhir/Practitioner | praticien |
      | un praticien supprime un praticien | clinician | DELETE | /fhir/Practitioner/$clinician | praticien |
      | un praticien crée un profil | clinician | POST | /fhir/PractitionerRole | profil praticien |
      | un patient modifie un profil | patient | PUT | /fhir/PractitionerRole/$profile | profil praticien |
      | un patient crée un jeu de valeurs | patient | POST | /fhir/ValueSet | jeu de valeurs de spécialité |
      | un praticien modifie un jeu de valeurs | clinician | PUT | /fhir/ValueSet/$specialty | jeu de valeurs de spécialité |
      | un patient supprime un jeu de valeurs | patient | DELETE | /fhir/ValueSet/$specialty | jeu de valeurs de spécialité |

  Scenario: L'admin seul crée, modifie et supprime `Organization`, `Location`, `HealthcareService`, `CodeSystem`, `ValueSet`, `Practitioner` et `PractitionerRole` ; tout autre utilisateur reçoit `forbidden`. (une spécialité est son `CodeSystem` et son `ValueSet`)
    When "admin" creates the "jeu de valeurs de spécialité" in FHIR
    Then the written specialty reads as a "CodeSystem" and a "ValueSet" of the same id and title
    When "admin" deletes the written "ValueSet"
    Then the written specialty is gone as a "CodeSystem" too

  Scenario: L'admin crée, modifie et supprime aussi `Patient`.
    When "admin" creates the "patient" in FHIR
    Then the client is answered 201 with the "Patient" written
    And the answer carries no temporary password
    When "admin" renames the written "Patient" under its version
    Then the client is answered 200 with the "Patient" renamed
    When "admin" deletes the written "Patient"
    Then the client is answered 204 and the written "Patient" is gone

  Scenario Outline: L'admin crée, modifie et supprime aussi `Patient`. (<case>)
    When "<who>" sends "<method>" to "<path>" with the "patient"
    Then the client is refused with 403 and the code "forbidden"
    And no audit entry was left

    Examples:
      | case                                  | who       | method | path                  |
      | un praticien ne crée pas de patient   | clinician | POST   | /fhir/Patient         |
      | un patient ne supprime pas sa fiche   | patient   | DELETE | /fhir/Patient/$patient |
      | un praticien ne modifie pas un patient | clinician | PUT | /fhir/Patient/$patient |

  Scenario: L'admin crée, modifie et supprime aussi `Patient`. (le téléphone et la naissance restent au patient)
    When "admin" creates the "patient" in FHIR
    And "admin" changes the birth date of the written "Patient" under its version
    Then the client is refused with 403 and the code "forbidden"

  Scenario: Les extensions portent ce que FHIR n'a pas : étage, capacité et équipements de la salle ; durée, battement, couleur, salle exigée et réservable en ligne du type ; poids round robin du profil.
    When "admin" creates the "salle" in FHIR
    Then the stored room has the floor "2", the capacity 4 and the equipment "ECG, Tapis"
    When "admin" creates the "type de RDV" in FHIR
    Then the stored type lasts 45 minutes plus 10, is coloured "#AA3366", needs a room and is booked offline
    When "admin" creates the "profil praticien" in FHIR
    Then the stored profile weighs 5 in round robin
    And the written "PractitionerRole" shows the round robin weight 5

  Scenario: Les règles sont celles de la console : codes uniques, refus `has_dependents` avec ce qui dépend encore de l'enregistrement, salle qui ne change pas de département tant que des praticiens de l'ancien l'ont par défaut, admin qui ne désactive pas son propre compte ni ne change son propre rôle. (code déjà utilisé)
    When "admin" creates the "hôpital" with the code of "lille"
    Then the client is refused with 400 and the code "invalid_input"
    And the outcome names the field "code" with the console's message "Ce code est déjà utilisé."

  Scenario: Les règles sont celles de la console : codes uniques, refus `has_dependents` avec ce qui dépend encore de l'enregistrement, salle qui ne change pas de département tant que des praticiens de l'ancien l'ont par défaut, admin qui ne désactive pas son propre compte ni ne change son propre rôle. (dépendants)
    When "admin" sends "DELETE" to "/fhir/Organization/$cardiology" with the "département"
    Then the client is refused with 409 and the code "has_dependents"
    And the outcome lists the room "room", the types "online, offline" and the profiles "profile, former_profile"

  Scenario: Les règles sont celles de la console : codes uniques, refus `has_dependents` avec ce qui dépend encore de l'enregistrement, salle qui ne change pas de département tant que des praticiens de l'ancien l'ont par défaut, admin qui ne désactive pas son propre compte ni ne change son propre rôle. (salle par défaut)
    When "admin" moves the room "room" to another department under its version
    Then the client is refused with 409 and the code "has_dependents"
    And the outcome lists the profiles "profile"

  Scenario Outline: Les règles sont celles de la console : codes uniques, refus `has_dependents` avec ce qui dépend encore de l'enregistrement, salle qui ne change pas de département tant que des praticiens de l'ancien l'ont par défaut, admin qui ne désactive pas son propre compte ni ne change son propre rôle. (<case>)
    When "admin" sends their own practitioner with "<change>" under its version
    Then the client is refused with 400 and the code "invalid_input"
    And the outcome names the field "<field>" with the console's message "<message>"

    Examples:
      | case                 | change           | field  | message                                            |
      | propre compte        | inactive         | active | Vous ne pouvez pas désactiver votre propre compte. |
      | propre rôle          | role clinician   | role   | Vous ne pouvez pas changer votre propre rôle.      |

  Scenario Outline: Une mise à jour avec un `If-Match` périmé échoue en 412. (<case>)
    When "admin" creates the "<sample>" in FHIR
    And "admin" renames the written "<resource>" under a stale version
    Then the client is refused with 412 and the code "conflict"
    And the written "<resource>" keeps its name

    Examples:
      | case             | sample           | resource          |
      | hôpital          | hôpital          | Organization      |
      | département      | département      | Organization      |
      | salle            | salle            | Location          |
      | type de RDV      | type de RDV      | HealthcareService |
      | spécialité       | spécialité       | CodeSystem        |
      | jeu de valeurs de spécialité | jeu de valeurs de spécialité | ValueSet |
      | praticien        | praticien        | Practitioner      |
      | profil praticien | profil praticien | PractitionerRole  |
      | patient          | patient          | Patient           |

  Scenario Outline: Chaque écriture laisse la même entrée d'audit que la console. (<case>)
    When "admin" creates, renames and deletes the "<sample>" in FHIR
    And "admin" creates, renames and deletes the "<sample>" on the console
    Then both leave the same audit entries "<actions>"

    Examples:
      | case             | sample           | actions                                                                  |
      | hôpital          | hôpital          | hospital.created, hospital.updated, hospital.deleted                     |
      | département      | département      | department.created, department.updated, department.deleted               |
      | salle            | salle            | room.created, room.updated, room.deleted                                 |
      | type de RDV      | type de RDV      | appointment_type.created, appointment_type.updated, appointment_type.deleted |
      | spécialité       | spécialité       | specialty.created, specialty.updated, specialty.deleted                  |
      | jeu de valeurs de spécialité | jeu de valeurs de spécialité | specialty.created, specialty.updated, specialty.deleted |
      | praticien        | praticien        | user.created, user.updated, user.deleted                                 |
      | profil praticien | profil praticien | clinician_profile.created, clinician_profile.updated, clinician_profile.deleted |
      | patient          | patient          | user.created, user.updated, user.deleted                                 |
