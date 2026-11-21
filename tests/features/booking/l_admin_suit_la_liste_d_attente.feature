Feature: L'admin suit la liste d'attente
  En tant qu'admin
  Je veux voir les entrées de la liste d'attente filtrées par statut
  Afin de savoir qui attend et depuis quand

  Background:
    Given 21 patients waiting in "Hôpital Nord" and "Hôpital Sud", one joining every minute
    And one expired entry joined before them all

  Scenario: La liste montre les entrées de tous les hôpitaux, des plus anciennes aux plus récentes, filtrées par statut, par pages de 20 avec le total.
    When the admin lists the "WAITING" entries, page "1"
    Then the list shows the 20 oldest waiting entries, oldest first, out of 21
    And the list holds entries of "Hôpital Nord, Hôpital Sud"
    When the admin lists the "WAITING" entries, page "2"
    Then the list shows the newest waiting entry only, out of 21
    When the admin lists the "EXPIRED" entries, page "1"
    Then the list shows the expired entry only, out of 1

  Scenario: Un filtre inutilisable dans l'adresse revient à la valeur par défaut au lieu de faire échouer la page.
    When the admin lists the "bogus" entries, page "abc"
    Then the list starts with the expired entry, then the oldest waiting ones, out of 22
