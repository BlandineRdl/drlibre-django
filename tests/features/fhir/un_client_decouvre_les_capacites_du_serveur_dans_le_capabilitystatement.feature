Feature: Un client découvre les capacités du serveur dans le CapabilityStatement
  En tant que client API
  Je veux lire sans jeton ce que le serveur FHIR sert
  Afin de me configurer sans lire la documentation du produit

  Scenario: `GET /fhir/metadata` renvoie sans jeton un `CapabilityStatement` FHIR 4.0.1 au format `application/fhir+json`.
    When a client without a token reads the capability statement
    Then the answer is a FHIR 4.0.1 CapabilityStatement in application/fhir+json

  Scenario: Il liste chaque ressource servie avec ses interactions, ses paramètres de recherche, ses `_include` et ses paramètres `_sort`.
    When a client without a token reads the capability statement
    Then each served resource is listed with its interactions, search parameters, includes and sorts

  Scenario: Il ne déclare rien que le serveur ne serve pas, et le serveur ne sert rien qu'il ne déclare pas. (routes)
    Then every served route is declared and every declared route is served

  Scenario: Il ne déclare rien que le serveur ne serve pas, et le serveur ne sert rien qu'il ne déclare pas. (interactions non déclarées)
    When an admin tries every interaction a declared resource does not declare
    Then each answers 405 not-supported allowing only the declared methods

  Scenario: Il ne déclare rien que le serveur ne serve pas, et le serveur ne sert rien qu'il ne déclare pas. (paramètres, `_include` et `_sort` déclarés)
    When an admin searches every declared resource
    Then each search reads every parameter, include and sort it declares

  Scenario: Il ne déclare rien que le serveur ne serve pas, et le serveur ne sert rien qu'il ne déclare pas. (paramètres, `_include` et `_sort` non déclarés)
    When an admin searches every declared resource with an undeclared parameter, include or sort
    Then each search is refused with 400 and the code "invalid_input"
