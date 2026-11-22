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
    When a client without a token searches "/fhir/ValueSet?status=active"
    Then the bundle holds only "ValueSet" "$specialty"
    When a client without a token reads "/fhir/ValueSet/$specialty"
    Then the value set includes the code system of "$specialty" only

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

  Scenario: Les recherches acceptent les paramètres du §15.5 pour ces ressources et `_include` `PractitionerRole:practitioner`, `PractitionerRole:organization`, `Slot:schedule`. (plage incluse)
    Given on "2026-11-20" the clinician is held at "09:00", booked at "10:00" and off at "11:00" on "2026-11-23"
    When a client without a token searches "/fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-11-24T00:00:00%2B01:00&_include=Slot:schedule"
    Then the FHIR slots are "09:30 free, 10:30 free, 11:30 free"
    And the bundle includes only "Schedule" "$rule"

  Scenario: Une recherche `Slot` exige `service-type` et une plage `start` de 31 jours au plus, sinon `invalid_input` ; elle renvoie seulement les créneaux libres de §5.1, avec un id stable pour un même schedule, type et début. (créneaux libres)
    Given on "2026-11-20" the clinician is held at "09:00", booked at "10:00" and off at "11:00" on "2026-11-23"
    When a client without a token searches "/fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-11-24T00:00:00%2B01:00"
    Then the FHIR slots are "09:30 free, 10:30 free, 11:30 free"
    And every slot is of "$online" on "Schedule/$rule" with its stable id

  Scenario: Une recherche `Slot` exige `service-type` et une plage `start` de 31 jours au plus, sinon `invalid_input` ; elle renvoie seulement les créneaux libres de §5.1, avec un id stable pour un même schedule, type et début. (id stable et lecture)
    Given on "2026-11-20" the clinician is held at "09:00", booked at "10:00" and off at "11:00" on "2026-11-23"
    When a client without a token searches "/fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-11-24T00:00:00%2B01:00"
    And the client searches the same slots again
    Then the ids are the same as before
    When the client reads the first slot
    Then the answer is a FHIR Slot "free"

  Scenario Outline: Une recherche `Slot` exige `service-type` et une plage `start` de 31 jours au plus, sinon `invalid_input` ; elle renvoie seulement les créneaux libres de §5.1, avec un id stable pour un même schedule, type et début. (praticien ou plage : <case>)
    Given on "2026-11-20" the clinician is held at "09:00", booked at "10:00" and off at "11:00" on "2026-11-23"
    When a client without a token searches "/fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-11-24T00:00:00%2B01:00&<narrowed>"
    Then the FHIR slots are "<slots>"

    Examples:
      | case               | narrowed                                | slots                               |
      | praticien          | schedule.actor=Practitioner/$clinician  | 09:30 free, 10:30 free, 11:30 free  |
      | plage              | schedule=Schedule/$rule                 | 09:30 free, 10:30 free, 11:30 free  |
      | ancien praticien   | schedule.actor=Practitioner/$former     |                                     |

  Scenario Outline: Une recherche `Slot` exige `service-type` et une plage `start` de 31 jours au plus, sinon `invalid_input` ; elle renvoie seulement les créneaux libres de §5.1, avec un id stable pour un même schedule, type et début. (fenêtre coupée par l'instant présent : <case>)
    Given on "2026-11-20" the clinician is held at "09:00", booked at "10:00" and off at "11:00" on "2026-11-23"
    When a client without a token searches "/fhir/Slot?service-type=$online&start=ge2026-11-16T00:00:00%2B01:00&start=lt<end>"
    Then the FHIR slots are ""

    Examples:
      | case                     | end                       |
      | période déjà passée      | 2026-11-17T00:00:00%2B01:00 |
      | période finissant maintenant | 2026-11-20T11:00:00%2B01:00 |

  Scenario Outline: Une recherche `Slot` exige `service-type` et une plage `start` de 31 jours au plus, sinon `invalid_input` ; elle renvoie seulement les créneaux libres de §5.1, avec un id stable pour un même schedule, type et début. (refus : <case>)
    When a client without a token reads "<path>"
    Then the answer is <status> with an OperationOutcome "<issue>" and the code "<code>"

    Examples:
      | case                 | path                                                                                          | status | issue     | code          |
      | sans type            | /fhir/Slot?start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-11-24T00:00:00%2B01:00                                                                              | 400    | invalid   | invalid_input |
      | sans borne de fin    | /fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00                           | 400    | invalid   | invalid_input |
      | plus de 31 jours     | /fhir/Slot?service-type=$online&start=ge2026-11-23T00:00:00%2B01:00&start=lt2026-12-25T00:00:00%2B01:00 | 400 | invalid | invalid_input |
      | id mal formé         | /fhir/Slot/abc                                                                                | 404    | not-found | not_found     |

  Scenario: Sans jeton, toute écriture renvoie `unauthenticated` (401). (mise à jour d'un `Patient`)
    Given two patients, a clinician who has seen the first one and an admin
    When a client without a token updates the patient "first"
    Then the answer is 401 with an OperationOutcome "login" and the code "unauthenticated"
    And the patient "first" has phone "0611111111" and birth date "1980-03-04"

  Scenario: Sans jeton, toute écriture renvoie `unauthenticated` (401). (chaque écriture déclarée)
    When a client without a token sends every write the server declares
    Then each write answers 401 with an OperationOutcome "login" and the code "unauthenticated"
