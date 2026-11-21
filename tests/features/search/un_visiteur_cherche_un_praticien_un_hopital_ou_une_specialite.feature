Feature: Un visiteur cherche un praticien, un hôpital ou une spécialité

  Background:
    Given the hospital "Hôpital Nord" in "Lille" at 50.63 3.06
    And the department "Pôle cœur" of "Hôpital Nord" offers "Bilan annuel" of 20 minutes online
    And the clinician "Dr Alice Martin" of "Rhumatologie" in "Pôle cœur"
    And the clinician "Dr Alice Martin" is titled "Rhumatologue" and presented as "Prend soin des articulations"
    And "Dr Alice Martin" is free at "2026-11-23 09:00"

  Scenario: La page d'accueil est la recherche ; elle s'ouvre sans session.
    When the visitor opens "/"
    Then the response status is 200
    And the page says "Dr Alice Martin"

  Scenario Outline: Le texte trouve, sans tenir compte de la casse et sur des mots partiels, le nom d'hôpital, la ville, le nom du praticien, la spécialité, le département et le type de RDV.
    When the visitor opens "/api/v1/search/providers?q=<query>"
    Then the listed names are "<result>"

    Examples:
      | query    | result          |
      | NORD     | Dr Alice Martin |
      | lil      | Dr Alice Martin |
      | marTIN   | Dr Alice Martin |
      | rhumato  | Dr Alice Martin |
      | cœur     | Dr Alice Martin |
      | BILAN    | Dr Alice Martin |

  Scenario: Les résultats forment trois listes entre lesquelles le visiteur bascule : praticiens, hôpitaux, spécialités.
    When the visitor opens "/?q=nord"
    Then the page says "Praticiens (1)"
    And the page says "Hôpitaux (1)"
    And the page says "Spécialités (1)"
    And the page links to "/?list=hospitals&q=nord"
    And the page links to "/?list=specialties&q=nord"

  Scenario: Un praticien montre nom complet, titre, spécialité, hôpital, département et ville.
    When the visitor opens "/api/v1/search/providers"
    Then "Dr Alice Martin" shows "full_name" equal to "Dr Alice Martin"
    And "Dr Alice Martin" shows "title" equal to "Rhumatologue"
    And "Dr Alice Martin" shows "specialty" equal to "Rhumatologie"
    And "Dr Alice Martin" shows "hospital" equal to "Hôpital Nord"
    And "Dr Alice Martin" shows "department" equal to "Pôle cœur"
    And "Dr Alice Martin" shows "city" equal to "Lille"

  Scenario: Un hôpital montre nom, adresse, ville, spécialités proposées et nombre de praticiens réservables.
    When the visitor opens "/api/v1/search/hospitals"
    Then "Hôpital Nord" shows "street" equal to "1 rue de la Paix"
    And "Hôpital Nord" shows "city" equal to "Lille"
    And "Hôpital Nord" shows "specialties" equal to "Rhumatologie"
    And "Hôpital Nord" shows "providers" equal to "1"

  Scenario: Une spécialité montre nom, nombre de praticiens et nombre d'hôpitaux.
    When the visitor opens "/api/v1/search/specialties"
    Then "Rhumatologie" shows "providers" equal to "1"
    And "Rhumatologie" shows "hospitals" equal to "1"

  Scenario: Seules les données réservables apparaissent : hôpitaux, praticiens et spécialités actifs, types actifs réservables en ligne ; un praticien sans type réservable en ligne dans son département n'est pas listé.
    Given the hospital "Hôpital Fermé" in "Paris" without coordinates
    And the department "Cardiologie fermée" of "Hôpital Fermé" offers "Consultation" of 20 minutes online
    And the clinician "Dr Hugo Fermé" of "Cardiologie" in "Cardiologie fermée"
    And "Dr Hugo Fermé" is free at "2026-11-23 09:00"
    And the hospital "Hôpital Fermé" is inactive
    And the department "Pôle téléphone" of "Hôpital Nord" offers "Appel" of 10 minutes by phone only
    And the clinician "Dr Paul Phone" of "Rhumatologie" in "Pôle téléphone"
    And the department "Pôle ancien" of "Hôpital Nord" offers "Ancienne consultation" of 10 minutes online
    And the type "Ancienne consultation" is inactive
    And the clinician "Dr Olga Ancienne" of "Rhumatologie" in "Pôle ancien"
    And the department "Pôle endormi" of "Hôpital Nord" offers "Consultation" of 20 minutes online
    And the clinician "Dr Sam Endormi" of "Dermatologie" in "Pôle endormi"
    And the specialty "Dermatologie" is inactive
    And the clinician "Dr Inès Partie" of "Rhumatologie" in "Pôle cœur"
    And the clinician "Dr Inès Partie" is inactive
    When the visitor opens "/api/v1/search/providers"
    Then the listed names are "Dr Alice Martin"
    When the visitor opens "/api/v1/search/hospitals"
    Then the listed names are "Hôpital Nord"
    When the visitor opens "/api/v1/search/specialties"
    Then the listed names are "Rhumatologie"

  Scenario: L'email, le téléphone et la date de naissance d'un praticien, et toute donnée de patient, ne sont jamais montrés.
    Given the clinician "Dr Alice Martin" has the email "alice.martin@clinique.example", the phone "0611223344" and the birth date "1980-02-03"
    When the visitor opens "/"
    And the visitor opens "/api/v1/search/providers"
    And the visitor opens "/providers/[id:Dr Alice Martin]"
    And the visitor opens "/api/v1/providers/[id:Dr Alice Martin]"
    Then no response ever said "alice.martin@clinique.example"
    And no response ever said "0611223344"
    And no response ever said "1980-02-03"

  Scenario Outline: 20 résultats par page par défaut, 10 ou 50 au choix ; la page montre le total, la page courante et le nombre de pages ; une page hors limites montre la dernière.
    Given 25 more clinicians named "Dr Bob" of "Rhumatologie" in "Pôle cœur"
    When the visitor opens "/api/v1/search/providers<address>"
    Then the response counts 26 results of <size> per page
    And the response lists <shown> items on page <page> of <pages>

    Examples:
      | address              | size | shown | page | pages |
      | ?q=                  | 20     | 20       | 1    | 2     |
      | ?size=10             | 10     | 10       | 1    | 3     |
      | ?size=50             | 50     | 26       | 1    | 1     |
      | ?size=10&page=3      | 10     | 6        | 3    | 3     |
      | ?page=99             | 20     | 6        | 2    | 2     |
      | ?size=7              | 20     | 20       | 1    | 2     |

  Scenario: La page montre le total, la page courante et le nombre de pages.
    Given 25 more clinicians named "Dr Bob" of "Rhumatologie" in "Pôle cœur"
    When the visitor opens "/?page=99"
    Then the page says "21 à 26 sur 26 praticiens · page 2 sur 2"

  Scenario: Texte, liste, taille et numéro de page vivent dans l'adresse : la recherche se partage, le bouton retour fonctionne, et une valeur inutilisable retombe sur sa valeur par défaut.
    Given 25 more clinicians named "Dr Bob" of "Rhumatologie" in "Pôle cœur"
    When the visitor opens "/?q=dr&size=10&page=2"
    Then the page says "11 à 20 sur 26 praticiens · page 2 sur 3"
    And the page links to "/?q=dr&size=10"
    And the page links to "/?q=dr&size=10&page=3"
    When the visitor opens "/?list=nimporte&size=7&page=abc&sort=distance&window=jamais&specialty=pas-un-id&from=hier"
    Then the response status is 200
    And the page says "1 à 20 sur 26 praticiens · page 1 sur 2"
    And the page never says "Distance la plus courte"

  Scenario: GET /search/providers, GET /search/hospitals et GET /search/specialties servent les mêmes résultats sans session.
    When the visitor opens "/?q=alice"
    Then the page says "Dr Alice Martin"
    When the visitor opens "/api/v1/search/providers?q=alice"
    Then the listed names are "Dr Alice Martin"
    When the visitor opens "/api/v1/search/hospitals?q=alice"
    Then the listed names are "Hôpital Nord"
    When the visitor opens "/api/v1/search/specialties?q=alice"
    Then the listed names are "Rhumatologie"
