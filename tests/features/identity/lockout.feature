Feature: Un compte est verrouillé après des échecs répétés
  En tant qu'admin
  Je veux que les tentatives répétées sur une adresse soient bloquées
  Afin que les mots de passe ne puissent pas être devinés

  Background:
    Given an active ADMIN "admin@example.org" with password "admin-password-1"

  Scenario: Après 10 échecs en 15 minutes sur une adresse, la connexion de cette adresse est refusée
    Given "admin@example.org" failed to sign in 10 times in 10 minutes
    When "admin@example.org" signs in with "admin-password-1"
    Then sign-in is refused with "Trop de tentatives pour cette adresse. Réessayez dans 15 minutes."
    And no session is opened

  Scenario: Après 10 échecs en 15 minutes sur une adresse, la connexion de cette adresse est refusée jusqu'à la fin de la fenêtre
    Given "admin@example.org" failed to sign in 10 times in 10 minutes
    When 15 minutes pass
    And "admin@example.org" signs in with "admin-password-1"
    Then a ADMIN session lasting 12 hours is opened

  Scenario: Après 10 échecs en 15 minutes sur une adresse, la connexion de cette adresse est refusée (9 échecs ne suffisent pas)
    Given "admin@example.org" failed to sign in 9 times in 5 minutes
    When "admin@example.org" signs in with "admin-password-1"
    Then a ADMIN session lasting 12 hours is opened

  Scenario: Une connexion réussie remet le compteur à zéro
    Given "admin@example.org" failed to sign in 9 times in 5 minutes
    And "admin@example.org" signs in with "admin-password-1"
    And "admin@example.org" failed to sign in 1 times in 1 minutes
    When "admin@example.org" signs in with "admin-password-1"
    Then a ADMIN session lasting 12 hours is opened

  Scenario: Le verrouillage est audité avec seulement le domaine de l'email
    Given "admin@example.org" failed to sign in 10 times in 10 minutes
    When "admin@example.org" signs in with "admin-password-1"
    Then the audit holds "auth.login_locked" with email domain "example.org"

  Scenario: Règle §12.1 : après 20 échecs en une heure depuis un réseau, la connexion depuis ce réseau est refusée
    Given 20 sign-ins failed on as many addresses from one network in 30 minutes
    When "admin@example.org" signs in with "admin-password-1"
    Then sign-in is refused with "Trop de tentatives depuis ce réseau. Réessayez plus tard."
    And no session is opened

  Scenario: Règle §12.1 : après 20 échecs en une heure depuis un réseau, la connexion depuis ce réseau est refusée (un autre réseau reste ouvert)
    Given 20 sign-ins failed on as many addresses from one network in 30 minutes
    When the next sign-in comes from another network
    And "admin@example.org" signs in with "admin-password-1"
    Then a ADMIN session lasting 12 hours is opened

  Scenario: Règle §12.1 : après 20 échecs en une heure depuis un réseau, la connexion depuis ce réseau est refusée (les connexions réussies ne comptent pas)
    Given "admin@example.org" signed in with "admin-password-1" 25 times
    When "admin@example.org" signs in with "admin-password-1"
    Then a ADMIN session lasting 12 hours is opened
