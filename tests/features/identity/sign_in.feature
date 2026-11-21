Feature: Le personnel se connecte par mot de passe et arrive dans son espace
  En tant que membre du personnel (admin ou praticien)
  Je veux me connecter avec mon email et mon mot de passe
  Afin d'accéder à mon espace de travail

  Background:
    Given an active ADMIN "Admin@Example.org" with password "admin-password-1"
    And an active CLINICIAN "clinician@example.org" with password "clinic-password-1"
    And an active PATIENT "patient@example.org" with password "patient-password-1"
    And an inactive CLINICIAN "gone@example.org" with password "gone-password-1"

  Scenario Outline: Une connexion réussie mène l'admin à la console admin, le praticien à son espace, et le patient avec mot de passe à la page d'accueil du portail. (<case>)
    When "<email>" signs in on the sign-in page with "<password>"
    Then they land on "<home>"
    And the page "<home>" opens

    Examples:
      | case                    | email                 | password           | home        |
      | admin                   | admin@example.org     | admin-password-1   | /console/   |
      | praticien               | clinician@example.org | clinic-password-1  | /workspace/ |
      | patient avec mot de passe | patient@example.org | patient-password-1 | /portal/    |

  Scenario Outline: Un email inconnu et un mauvais mot de passe donnent le même message, dans le même temps de réponse (<case>)
    When "<email>" signs in with "<password>"
    Then sign-in is refused with "Email ou mot de passe incorrect."
    And exactly 1 password check ran
    And no session is opened

    Examples:
      | case                | email              | password         |
      | email inconnu       | nobody@example.org | admin-password-1 |
      | mauvais mot de passe | admin@example.org | wrong-password-1 |

  Scenario: Un utilisateur inactif ne peut pas se connecter
    When "gone@example.org" signs in with "gone-password-1"
    Then sign-in is refused with "Email ou mot de passe incorrect."
    And no session is opened

  Scenario: La session dure 12 h pour un admin et 7 jours pour les autres ; elle repart pour une durée pleine quand il en reste moins de la moitié (admin)
    When "admin@example.org" signs in with "admin-password-1"
    Then a ADMIN session lasting 12 hours is opened

  Scenario: La session dure 12 h pour un admin et 7 jours pour les autres ; elle repart pour une durée pleine quand il en reste moins de la moitié (autres)
    When "Clinician@example.org" signs in with "clinic-password-1"
    Then a CLINICIAN session lasting 168 hours is opened

  Scenario: La session dure 12 h pour un admin et 7 jours pour les autres ; elle repart pour une durée pleine quand il en reste moins de la moitié (repart)
    Given "clinician@example.org" signed in
    When 4 days pass
    And the session is used
    Then the session expires 7 days from now
    And the session was renewed

  Scenario: La session dure 12 h pour un admin et 7 jours pour les autres ; elle repart pour une durée pleine quand il en reste moins de la moitié (pas avant la moitié)
    Given "clinician@example.org" signed in
    When 2 days pass
    And the session is used
    Then the session expires 5 days from now

  Scenario: La session dure 12 h pour un admin et 7 jours pour les autres ; elle repart pour une durée pleine quand il en reste moins de la moitié (admin, au-delà elle ne vaut plus)
    Given "admin@example.org" signed in
    When 13 hours pass
    And the session is used
    Then nobody is identified

  Scenario: La déconnexion supprime la session
    Given "admin@example.org" signed in
    When the session is signed out
    Then no session is opened

  Scenario: La connexion et la déconnexion sont aussi disponibles par l'API `POST /auth/login` et `POST /auth/logout` (§14)
    When "clinician@example.org" signs in through the API with "clinic-password-1"
    Then the API answers 200 with role "CLINICIAN" and home "/workspace/"
    When they sign out through the API
    Then the API answers 204
    And no session is opened

  Scenario: La réussite et l'échec sont audités avec seulement le domaine de l'email (réussite)
    When "admin@example.org" signs in with "admin-password-1"
    Then the audit holds "auth.login_succeeded" with email domain "example.org"
    And the last login time of "admin@example.org" is now

  Scenario: La réussite et l'échec sont audités avec seulement le domaine de l'email (échec)
    When "admin@example.org" signs in with "wrong-password-1"
    Then the audit holds "auth.login_failed" with email domain "example.org"
