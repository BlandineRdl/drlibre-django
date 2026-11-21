Feature: L'admin gère les comptes utilisateurs
  En tant qu'admin
  Je veux créer des comptes avec un mot de passe temporaire et les modifier
  Afin que le personnel et les patients créés par l'admin puissent se connecter

  Background:
    Given the signed-in admin "admin@example.org"

  Scenario: La liste se cherche par nom ou par email ; l'email est unique et enregistré en minuscules (recherche)
    Given a CLINICIAN account named "Ana Bel" with email "ana.bel@example.org"
    And a PATIENT account named "Paul Martin" with email "paul@example.org"
    When the admin searches users for "bel"
    Then the users found are "ana.bel@example.org"
    When the admin searches users for "paul@"
    Then the users found are "paul@example.org"

  Scenario: La liste se cherche par nom ou par email ; l'email est unique et enregistré en minuscules (enregistré en minuscules)
    When the admin creates the CLINICIAN "Ana Bel" with email "Ana@Example.org" and password "temporary-pass-1"
    Then the user "ana@example.org" exists and must change password

  Scenario: La liste se cherche par nom ou par email ; l'email est unique et enregistré en minuscules (unique, quelle que soit sa casse)
    Given a CLINICIAN account "ana@example.org"
    When the admin creates the PATIENT "Ana Bis" with email "ANA@example.org" and password "temporary-pass-1"
    Then the write is refused as invalid on "email"

  Scenario: Règle §8 et §10 : le compte est créé avec un mot de passe temporaire, de 10 à 72 caractères (trop court)
    When the admin creates the PATIENT "Paul" with email "paul@example.org" and password "short"
    Then the write is refused as invalid on "temporary_password"

  Scenario: Règle §8 et §10 : le compte est créé avec un mot de passe temporaire, de 10 à 72 caractères (trop long)
    When the admin creates the PATIENT "Paul" with email "paul@example.org" and password "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    Then the write is refused as invalid on "temporary_password"

  Scenario: Le nom, l'email, le rôle et l'état actif sont modifiables
    Given a CLINICIAN account "ana@example.org"
    When the admin renames "ana@example.org" to "Ana Belle" with email "ana.belle@example.org", role "PATIENT" and active "false"
    Then the user "ana.belle@example.org" is the PATIENT "Ana Belle", inactive
    And the audit holds "user.updated" changing "email,full_name,role,active"

  Scenario: Un admin ne peut ni désactiver son propre compte, ni changer son propre rôle (désactivation)
    When the admin edits their own account setting active "false"
    Then the write is refused as invalid on "active"

  Scenario: Un admin ne peut ni désactiver son propre compte, ni changer son propre rôle (rôle)
    When the admin edits their own account setting role "CLINICIAN"
    Then the write is refused as invalid on "role"

  Scenario: Désactiver un utilisateur coupe ses sessions immédiatement
    Given a CLINICIAN account "ana@example.org" that is signed in
    When the admin edits "ana@example.org" setting active "false"
    Then the session of "ana@example.org" no longer identifies anyone
    And the audit holds "user.updated" closing 1 session

  Scenario: Un praticien qui a des RDV actifs à venir ne peut pas être désactivé ; le refus liste ces RDV
    Given a CLINICIAN account "ana@example.org"
    And "ana@example.org" has an active appointment in 2 days
    And "ana@example.org" has a cancelled appointment in 3 days
    When the admin edits "ana@example.org" setting active "false"
    Then the write is refused listing 1 appointment

  Scenario: La suppression est refusée pour son propre compte et pour un utilisateur qui est l'acteur d'entrées d'audit ; le message invite à désactiver le compte (son propre compte)
    When the admin deletes "admin@example.org"
    Then the write is refused as "forbidden" inviting to deactivate

  Scenario: La suppression est refusée pour son propre compte et pour un utilisateur qui est l'acteur d'entrées d'audit ; le message invite à désactiver le compte (acteur d'entrées d'audit)
    Given a CLINICIAN account "ana@example.org" that is signed in
    When the admin deletes "ana@example.org"
    Then the write is refused as "has_dependents" inviting to deactivate

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle (création)
    When the admin creates the CLINICIAN "Ana Bel" with email "Ana@Example.org" and password "temporary-pass-1"
    Then the audit holds "user.created" with only "role"

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle (suppression)
    Given a PATIENT account "paul@example.org"
    When the admin deletes "paul@example.org"
    Then no user "paul@example.org" exists
    And the audit holds "user.deleted" with only "role"

  Scenario: Un praticien qui a un profil ne peut être ni supprimé ni changé de rôle tant que ce profil existe ; le refus le dit (suppression)
    Given a CLINICIAN account "ana@example.org"
    And "ana@example.org" has a clinician profile
    When the admin deletes "ana@example.org"
    Then the write is refused as "has_dependents" inviting to deactivate

  Scenario: Un praticien qui a un profil ne peut être ni supprimé ni changé de rôle tant que ce profil existe ; le refus le dit (changement de rôle)
    Given a CLINICIAN account "ana@example.org"
    And "ana@example.org" has a clinician profile
    When the admin edits "ana@example.org" setting role "PATIENT"
    Then the write is refused as invalid on "role"
