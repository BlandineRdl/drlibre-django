Feature: Le visiteur consulte les pages publiques des praticiens, hôpitaux et spécialités

  Background:
    Given the hospital "Hôpital Nord" in "Lille" at 50.63 3.06
    And the department "Cardiologie" of "Hôpital Nord" offers "Consultation cardio" of 20 minutes online
    And the department "Cardiologie" of "Hôpital Nord" offers "Bilan long" of 60 minutes online
    And the clinician "Dr Alice Martin" of "Cardiologie" in "Cardiologie"
    And the clinician "Dr Alice Martin" is titled "Cardiologue" and presented as "Cardiologue interventionnelle"
    And the clinician "Dr Bruno Petit" of "Cardiologie" in "Cardiologie"
    And the department "Pédiatrie" of "Hôpital Nord" offers "Consultation pédiatrie" of 30 minutes online
    And the clinician "Dr Chloé Durand" of "Pédiatrie" in "Pédiatrie"
    And "Dr Alice Martin" is free at "2026-11-23 09:00, 2026-11-25 14:00"
    And "Dr Alice Martin" is free at "2026-11-24 10:00" for "Bilan long"
    And "Dr Bruno Petit" is free at "2026-11-26 09:00"

  Scenario: Un résultat praticien mène à sa page par un lien vers tous ses horaires.
    When the visitor opens "/?q=alice"
    Then the page says "Tous les horaires"
    And the page links to "/providers/[id:Dr Alice Martin]"

  Scenario: La page praticien montre nom, titre, spécialité, bio, hôpital et département, ses types réservables en ligne, et un bandeau des créneaux libres du type choisi, du lundi au dimanche, avec semaine précédente et suivante.
    When the visitor opens "/providers/[id:Dr Alice Martin]?week=2026-11-23"
    Then the response status is 200
    And the page says "Dr Alice Martin"
    And the page says "Cardiologue · Cardiologie"
    And the page says "Cardiologue interventionnelle"
    And the page says "Hôpital Nord · Cardiologie · Lille"
    And the page says "Consultation cardio 20 min"
    And the page says "Bilan long 60 min"
    And the page says "Semaine du lun. 23/11 au dim. 29/11"
    And the page says "09:00"
    And the page says "14:00"
    And the page says "Aucun créneau"
    And the page links to "/booking/new?type=[type:Consultation cardio]&clinician=[id:Dr Alice Martin]&start=2026-11-23T08:00:00Z"
    And the page links to "/providers/[id:Dr Alice Martin]?type=[type:Consultation cardio]&week=2026-11-16"
    And the page links to "/providers/[id:Dr Alice Martin]?type=[type:Consultation cardio]&week=2026-11-30"
    When the visitor opens "/providers/[id:Dr Alice Martin]?type=[type:Bilan long]&week=2026-11-23"
    Then the page says "10:00"
    And the page never says "14:00"
    When the visitor opens "/providers/[id:Dr Alice Martin]"
    Then the page says "Aucun créneau libre cette semaine."
    And the page says "Passé"
    And the page says "Prochain créneau libre : lun. 23/11 à 09:00"
    And the page links to "/providers/[id:Dr Alice Martin]?type=[type:Consultation cardio]&week=2026-11-23"

  Scenario Outline: La semaine par défaut est celle d'aujourd'hui ; la navigation s'arrête à l'horizon de 90 jours.
    When the visitor opens "/providers/[id:Dr Alice Martin]<address>"
    Then the page says "<label>"
    And the page <previous> "Semaine précédente"
    And the page <next> "Semaine suivante"

    Examples:
      | address            | label                              | previous    | next        |
      | ?week=             | Semaine du lun. 16/11 au dim. 22/11 | never says  | says        |
      | ?week=2027-02-15   | Semaine du lun. 15/02 au dim. 21/02 | says        | never says  |
      | ?week=2027-02-22   | Semaine du lun. 16/11 au dim. 22/11 | never says  | says        |
      | ?week=nimporte     | Semaine du lun. 16/11 au dim. 22/11 | never says  | says        |
      | ?week=2026-11-09   | Semaine du lun. 16/11 au dim. 22/11 | never says  | says        |

  Scenario: La page hôpital montre nom, adresse, téléphone, description, départements, spécialités et praticiens, chacun avec ses prochains créneaux libres.
    When the visitor opens "/hospitals/[hospital:Hôpital Nord]"
    Then the response status is 200
    And the page says "Hôpital Nord"
    And the page says "1 rue de la Paix, 59000 Lille, France"
    And the page says "+33 3 20 00 00 00"
    And the page says "Description de Hôpital Nord"
    And the page says "Pédiatrie"
    And the page says "Dr Alice Martin"
    And the page says "Dr Bruno Petit"
    And the page says "lun. 23/11 09:00"
    And the page says "Premier disponible"
    And the page links to "/booking/new?type=[type:Consultation cardio]&department=[department:Cardiologie]&start=2026-11-23T08:00:00Z"

  Scenario: La page spécialité montre la liste des praticiens de cette spécialité.
    When the visitor opens "/specialties/[specialty:Cardiologie]"
    Then the response status is 200
    And the page says "Dr Alice Martin"
    And the page says "Dr Bruno Petit"
    And the page never says "Dr Chloé Durand"

  Scenario Outline: Ces pages s'ouvrent sans session et ne montrent aucune donnée non publique ; un enregistrement absent ou inactif donne `not_found`.
    Given the clinician "Dr Alice Martin" has the email "alice.martin@clinique.example", the phone "0611223344" and the birth date "1980-02-03"
    And the hospital "Hôpital Fermé" in "Paris" without coordinates
    And the department "Pôle fermé" of "Hôpital Fermé" offers "Consultation" of 20 minutes online
    And the clinician "Dr Hugo Fermé" of "Fermée" in "Pôle fermé"
    And the hospital "Hôpital Fermé" is inactive
    And the department "Pôle sans ligne" of "Hôpital Nord" offers "Appel" of 10 minutes by phone only
    And the clinician "Dr Paul Phone" of "Cardiologie" in "Pôle sans ligne"
    And the clinician "Dr Inès Partie" of "Cardiologie" in "Cardiologie"
    And the clinician "Dr Inès Partie" is inactive
    And the specialty "Fermée" is inactive
    When the visitor opens "<address>"
    Then the response status is <status>
    And no response ever said "alice.martin@clinique.example"
    And no response ever said "0611223344"

    Examples:
      | address                                   | status |
      | /providers/[id:Dr Alice Martin]           | 200    |
      | /hospitals/[hospital:Hôpital Nord]        | 200    |
      | /specialties/[specialty:Cardiologie]      | 200    |
      | /providers/00000000-0000-4000-8000-000000000000 | 404 |
      | /providers/[id:Dr Inès Partie]            | 404    |
      | /providers/[id:Dr Paul Phone]             | 404    |
      | /providers/[id:Dr Hugo Fermé]             | 404    |
      | /hospitals/[hospital:Hôpital Fermé]       | 404    |
      | /specialties/[specialty:Fermée]           | 404    |

  Scenario: `GET /providers/{id}`, `GET /hospitals/{id}`, `GET /specialties/{id}` et `GET /slots` répondent sans session.
    When the visitor opens "/api/v1/providers/[id:Dr Alice Martin]?week=2026-11-23"
    Then the response status is 200
    And the week starts on "2026-11-23"
    And "Dr Alice Martin" lists the starts "2026-11-23 09:00, 2026-11-25 14:00" for the week
    When the visitor opens "/api/v1/hospitals/[hospital:Hôpital Nord]"
    Then the response status is 200
    When the visitor opens "/api/v1/specialties/[specialty:Cardiologie]"
    Then the response status is 200
    When the visitor opens "/api/v1/slots?type=[type:Consultation cardio]&clinician=[id:Dr Alice Martin]&start=2026-11-23T00:00:00Z&end=2026-11-24T00:00:00Z"
    Then the free slots start at "08:00" UTC
    When the visitor opens "/api/v1/providers/00000000-0000-4000-8000-000000000000"
    Then the response status is 404
    And the code is "not_found"
