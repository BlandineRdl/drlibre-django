Feature: Un client sans jeton découvre le référentiel et les créneaux libres
  En tant que client API
  Je veux lire sans jeton les hôpitaux, départements, salles, spécialités, types de RDV, praticiens et créneaux libres en FHIR R4
  Afin d'afficher l'offre de soins et ses disponibilités dans mon application

  Background:
    Given a reference directory of active and closed hospitals, their departments, rooms, types, specialties and clinicians

  Scenario: L'API sert FHIR R4 (4.0.1) en `application/fhir+json` sous `/fhir` ; chaque ressource garde l'id du produit comme id logique et porte `meta.versionId` et `meta.lastUpdated`.
    When a client without a token reads "/fhir/Organization/$lille"
    Then the answer is a FHIR "Organization" with the id of "lille"
    And it carries a version, its last update and the version as ETag

  Scenario Outline: Sans jeton, lecture et recherche sont ouvertes sur les enregistrements actifs : `Organization` (hôpital de type `prov`, département de type `dept` `partOf` l'hôpital), `Location` (site avec adresse, téléphone, position et fuseau ; salle `partOf` le site), `HealthcareService`, `CodeSystem` et `ValueSet` des spécialités, `Practitioner` et `PractitionerRole` limités aux champs publics, `Schedule`. (<case>)
    When a client without a token reads "<path>"
    Then the answer is a FHIR "<resource>" with the id of "<record>"

    Examples:
      | case               | path                                   | resource          | record     |
      | hôpital            | /fhir/Organization/$lille              | Organization      | lille      |
      | département        | /fhir/Organization/$cardiology         | Organization      | cardiology |
      | site               | /fhir/Location/$lille                  | Location          | lille      |
      | salle              | /fhir/Location/$room                   | Location          | room       |
      | type de RDV        | /fhir/HealthcareService/$online        | HealthcareService | online     |
      | spécialité         | /fhir/CodeSystem/$specialty            | CodeSystem        | specialty  |
      | praticien          | /fhir/Practitioner/$clinician          | Practitioner      | clinician  |
      | profil du praticien | /fhir/PractitionerRole/$profile       | PractitionerRole  | profile    |
      | plage              | /fhir/Schedule/$rule                   | Schedule          | rule       |

  Scenario: Sans jeton, lecture et recherche sont ouvertes sur les enregistrements actifs : `Organization` (hôpital de type `prov`, département de type `dept` `partOf` l'hôpital), `Location` (site avec adresse, téléphone, position et fuseau ; salle `partOf` le site), `HealthcareService`, `CodeSystem` et `ValueSet` des spécialités, `Practitioner` et `PractitionerRole` limités aux champs publics, `Schedule`. (hôpital et département)
    When a client without a token reads "/fhir/Organization/$cardiology"
    Then the organization is of type "dept" and part of "Organization/$lille"
    When a client without a token reads "/fhir/Organization/$lille"
    Then the organization is of type "prov"

  Scenario: Sans jeton, lecture et recherche sont ouvertes sur les enregistrements actifs : `Organization` (hôpital de type `prov`, département de type `dept` `partOf` l'hôpital), `Location` (site avec adresse, téléphone, position et fuseau ; salle `partOf` le site), `HealthcareService`, `CodeSystem` et `ValueSet` des spécialités, `Practitioner` et `PractitionerRole` limités aux champs publics, `Schedule`. (site et salle)
    When a client without a token reads "/fhir/Location/$lille"
    Then the site shows its address in "Lille", its phone, its position and the time zone "Europe/Paris"
    When a client without a token reads "/fhir/Location/$room"
    Then the room is part of "Location/$lille"

  Scenario: Sans jeton, lecture et recherche sont ouvertes sur les enregistrements actifs : `Organization` (hôpital de type `prov`, département de type `dept` `partOf` l'hôpital), `Location` (site avec adresse, téléphone, position et fuseau ; salle `partOf` le site), `HealthcareService`, `CodeSystem` et `ValueSet` des spécialités, `Practitioner` et `PractitionerRole` limités aux champs publics, `Schedule`. (spécialités)
    When a client without a token searches "/fhir/CodeSystem?status=active"
    Then the bundle holds only "CodeSystem" "$specialty"
    When a client without a token reads "/fhir/ValueSet/specialties"
    Then the value set gathers the code system of "$specialty" only

  Scenario: Un enregistrement inactif ou absent donne `not_found` ; l'email et le téléphone d'un praticien ne sont pas renvoyés.
    When a client without a token reads "/fhir/Organization/$roubaix"
    Then the answer is 404 with an OperationOutcome "not-found" and the code "not_found"
    When a client without a token reads "/fhir/Practitioner/$former"
    Then the answer is 404 with an OperationOutcome "not-found" and the code "not_found"
    When a client without a token reads "/fhir/Location/00000000-0000-0000-0000-000000000000"
    Then the answer is 404 with an OperationOutcome "not-found" and the code "not_found"
    When a client without a token reads "/fhir/Practitioner/$clinician"
    Then the practitioner shows "Alice Martin" titled "Dr" without email or phone

  Scenario Outline: Les recherches acceptent les paramètres du §15.5 pour ces ressources et `_include` `PractitionerRole:practitioner`, `PractitionerRole:organization`, `Slot:schedule`. (<case>)
    When a client without a token searches "<search>"
    Then the bundle holds only "<resource>" "<records>"

    Examples:
      | case                         | search                                                         | resource          | records       |
      | hôpitaux d'une ville         | /fhir/Organization?type=prov&address-city=Lille                 | Organization      | $lille        |
      | départements d'un hôpital    | /fhir/Organization?partof=Organization/$lille                   | Organization      | $cardiology   |
      | sites à proximité            | /fhir/Location?near=50.63\|3.06\|10\|km                         | Location          | $lille        |
      | salles d'un site             | /fhir/Location?partof=Location/$lille                           | Location          | $room         |
      | types d'une spécialité       | /fhir/HealthcareService?specialty=$specialty                    | HealthcareService | $online       |
      | praticiens par nom           | /fhir/Practitioner?name=alice                                   | Practitioner      | $clinician    |
      | plages d'un praticien à une date | /fhir/Schedule?actor=Practitioner/$clinician&date=2026-06-01&active=true | Schedule | $rule |
      | aucune plage après l'horizon | /fhir/Schedule?actor=Practitioner/$clinician&date=ge2027-01-01  | Schedule          | none          |

  Scenario: Les recherches acceptent les paramètres du §15.5 pour ces ressources et `_include` `PractitionerRole:practitioner`, `PractitionerRole:organization`, `Slot:schedule`. (praticien et département inclus)
    When a client without a token searches "/fhir/PractitionerRole?specialty=$specialty&_include=PractitionerRole:practitioner&_include=PractitionerRole:organization"
    Then the bundle matches "PractitionerRole" "$profile"
    And the bundle includes "Practitioner" "$clinician" and "Organization" "$cardiology"

  Scenario: Une recherche renvoie un Bundle `searchset` avec `total` et les liens `self`, `next` et `previous` ; `_count` fixe la taille de page, 20 par défaut, 100 au plus ; `_sort` est accepté sur les paramètres listés.
    When a client without a token searches "/fhir/Organization?_count=2&_sort=-name"
    Then the searchset has a total of 3, the links "self, next" and the entries "Hôpital Sud, Hôpital Nord"
    When the client follows the "next" link
    Then the searchset has a total of 3, the links "self, previous" and the entries "Cardiologie"
    When a client without a token searches "/fhir/Organization"
    Then the searchset has a total of 3, the links "self" and the entries "Cardiologie, Hôpital Nord, Hôpital Sud"

  Scenario Outline: Chaque erreur est un `OperationOutcome` avec le statut HTTP du §4. (<case>)
    When a client without a token reads "<path>"
    Then the answer is <status> with an OperationOutcome "<issue>" and the code "<code>"

    Examples:
      | case                     | path                                   | status | issue     | code          |
      | ressource inconnue       | /fhir/Foo                              | 404    | not-found | not_found     |
      | paramètre non pris en charge | /fhir/Organization?colour=red      | 400    | invalid   | invalid_input |
      | référence mal formée     | /fhir/Schedule?actor=Patient/12        | 400    | invalid   | invalid_input |
