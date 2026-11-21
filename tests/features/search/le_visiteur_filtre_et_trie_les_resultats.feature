Feature: Le visiteur filtre et trie les résultats

  Background:
    Given the hospital "Hôpital Nord" in "Lille" at 50.63 3.06
    And the hospital "Hôpital Sud" in "Marseille" at 43.30 5.37
    And the hospital "Hôpital Sans Coordonnées" in "Lyon" without coordinates
    And the department "Cardiologie" of "Hôpital Nord" offers "Consultation cardio" of 20 minutes online
    And the department "Cardiologie" of "Hôpital Nord" offers "Bilan long" of 60 minutes online
    And the department "Pédiatrie" of "Hôpital Sud" offers "Consultation pédiatrie" of 30 minutes online
    And the department "Dermatologie" of "Hôpital Sans Coordonnées" offers "Consultation peau" of 15 minutes online
    And the clinician "Dr Alice Martin" of "Cardiologie" in "Cardiologie"
    And the clinician "Dr Alain Zola" of "Cardiologie" in "Cardiologie"
    And the clinician "Dr Bruno Petit" of "Pédiatrie" in "Pédiatrie"
    And the clinician "Dr Chloé Durand" of "Dermatologie" in "Dermatologie"
    And "Dr Alice Martin" is free at "2026-11-23 09:00"
    And "Dr Alain Zola" is free at "2026-11-20 14:00"
    And "Dr Bruno Petit" is free at "2026-11-23 14:00, 2026-11-24 18:00"
    And "Dr Chloé Durand" is free at "2026-11-23 18:30"

  Scenario Outline: Filtres facultatifs, combinés en ET : spécialité, hôpital, ville, type de RDV, date au plus tôt, fenêtre (toutes, aujourd'hui, sous 3 jours, sous 7 jours), moment de la journée (matin avant 12:00, après-midi de 12:00 à 17:00, soir après 17:00, dans le fuseau de l'hôpital).
    When the visitor opens "/api/v1/search/providers?<filters>"
    Then the listed names are "<result>"

    Examples:
      | filters                                         | result                                                   |
      | specialty=[specialty:Pédiatrie]                 | Dr Bruno Petit                                           |
      | hospital=[hospital:Hôpital Sud]                 | Dr Bruno Petit                                           |
      | city=LYO                                        | Dr Chloé Durand                                          |
      | type=[type:Consultation peau]                   | Dr Chloé Durand                                          |
      | from=2026-11-24                                 | Dr Bruno Petit                                           |
      | window=today                                    | Dr Alain Zola                                            |
      | window=3d                                       | Dr Alain Zola, Dr Alice Martin                           |
      | window=7d                                       | Dr Alain Zola, Dr Alice Martin, Dr Bruno Petit, Dr Chloé Durand |
      | moment=morning                                  | Dr Alice Martin                                          |
      | moment=afternoon                                | Dr Alain Zola, Dr Bruno Petit                            |
      | moment=evening                                  | Dr Chloé Durand, Dr Bruno Petit                          |
      | specialty=[specialty:Cardiologie]&moment=afternoon | Dr Alain Zola                                         |
      | window=7d&moment=evening&city=marseille         | Dr Bruno Petit                                           |

  Scenario Outline: Le moment de la journée est à gauche inclus et à droite exclu : 12:00 est l'après-midi, 17:00 le soir.
    Given the clinician "Dr Dan Midi" of "Cardiologie" in "Cardiologie"
    And the clinician "Dr Eva Soir" of "Cardiologie" in "Cardiologie"
    And "Dr Dan Midi" is free at "2026-11-23 12:00"
    And "Dr Eva Soir" is free at "2026-11-23 17:00"
    When the visitor opens "/api/v1/search/providers?specialty=[specialty:Cardiologie]&moment=<moment>"
    Then the listed names are "<result>"

    Examples:
      | moment    | result                       |
      | afternoon | Dr Alain Zola, Dr Dan Midi   |
      | evening   | Dr Eva Soir                  |

  Scenario: Avec un filtre de type, les créneaux sont calculés pour ce type.
    Given "Dr Alice Martin" is free at "2026-11-24 10:00" for "Bilan long"
    When the visitor opens "/api/v1/search/providers?type=[type:Bilan long]"
    Then the listed names are "Dr Alice Martin, Dr Alain Zola"
    And "Dr Alice Martin" shows the next starts "2026-11-24 10:00"
    And "Dr Alice Martin" shows the type "Bilan long"

  Scenario: Un filtre de temps change à la fois les résultats listés et les créneaux montrés.
    Given "Dr Alice Martin" is free at "2026-11-23 15:00"
    When the visitor opens "/api/v1/search/providers?specialty=[specialty:Cardiologie]&moment=afternoon&window=7d"
    Then the listed names are "Dr Alain Zola, Dr Alice Martin"
    And "Dr Alice Martin" shows the next starts "2026-11-23 15:00"
    When the visitor opens "/api/v1/search/providers?specialty=[specialty:Pédiatrie]&moment=morning"
    Then nothing is listed

  Scenario Outline: Tris : disponibilité la plus proche (par défaut), nom de A à Z, nom de Z à A, distance la plus courte.
    When the visitor opens "/api/v1/search/providers?<sort>"
    Then the listed names are "<result>"

    Examples:
      | sort                          | result                                                      |
      | sort=soonest                  | Dr Alain Zola, Dr Alice Martin, Dr Bruno Petit, Dr Chloé Durand |
      | sort=name                     | Dr Alain Zola, Dr Alice Martin, Dr Bruno Petit, Dr Chloé Durand |
      | sort=name-desc                | Dr Chloé Durand, Dr Bruno Petit, Dr Alice Martin, Dr Alain Zola |
      | sort=distance&lat=43.3&lon=5.37 | Dr Bruno Petit, Dr Alain Zola, Dr Alice Martin, Dr Chloé Durand |

  Scenario: Les hôpitaux sans coordonnées passent après les autres dans le tri par distance.
    When the visitor opens "/api/v1/search/hospitals?sort=distance&lat=50.63&lon=3.06"
    Then the listed names are "Hôpital Nord, Hôpital Sud, Hôpital Sans Coordonnées"
    And "Hôpital Nord" is about 0 km away
    And "Hôpital Sud" is about 835 km away

  Scenario: Le tri porte sur tout l'ensemble des résultats, pas sur la page ; les égalités se départagent par nom puis par id.
    Given 25 more clinicians named "Dr Nom" of "Cardiologie" in "Cardiologie"
    And two clinicians both named "Dr Jumeau" of "Cardiologie" in "Cardiologie"
    When the visitor opens "/api/v1/search/providers?sort=name-desc&size=10&q=nom"
    Then the listed names are "Dr Nom 25, Dr Nom 24, Dr Nom 23, Dr Nom 22, Dr Nom 21, Dr Nom 20, Dr Nom 19, Dr Nom 18, Dr Nom 17, Dr Nom 16"
    When the visitor opens "/api/v1/search/providers?sort=name&size=50&q=jumeau"
    Then the twins are listed by ascending id for "Dr Jumeau"

  Scenario: Le tri par distance part de la position donnée par le navigateur, sans service externe, et des coordonnées des hôpitaux ; sans position, il n'est pas proposé.
    When the visitor opens "/?sort=distance"
    Then the page never says "Distance la plus courte"
    And the page says "Trier par distance"
    When the visitor opens "/?sort=distance&lat=50.63&lon=3.06"
    Then the page says "Distance la plus courte"
    And the page says "à 0 km"

  Scenario: Filtres et tri vivent dans l'adresse de la page, et les trois `GET /search/providers`, `/search/hospitals`, `/search/specialties` les acceptent.
    When the visitor opens "/?q=dr&window=7d&moment=afternoon&sort=name-desc&size=10"
    Then the page links to "/?list=hospitals&q=dr&window=7d&moment=afternoon&sort=name-desc&size=10"
    When the visitor opens "/api/v1/search/providers?window=7d&moment=afternoon&sort=name-desc"
    Then the response status is 200
    When the visitor opens "/api/v1/search/hospitals?window=7d&moment=afternoon&sort=name-desc"
    Then the listed names are "Hôpital Sud, Hôpital Nord"
    When the visitor opens "/api/v1/search/specialties?window=7d&moment=afternoon&sort=name-desc"
    Then the listed names are "Pédiatrie, Cardiologie"
