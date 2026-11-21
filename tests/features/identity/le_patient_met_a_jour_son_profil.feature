Feature: Le patient met à jour son profil
  En tant que patient connecté, avec ou sans mot de passe
  Je veux modifier mon téléphone et ma date de naissance
  Afin que mes coordonnées restent justes

  Background:
    Given a patient "lea@example.org" named "Léa Martin" with phone "0601020304" born on "1990-05-17"

  Scenario: Le nom et l'email sont affichés, non modifiables.
    When the patient saves the phone "06 11 22 33 44" and the birth date "1990-05-18"
    Then the patient is still named "Léa Martin" with email "lea@example.org"
    And the profile offers no way to change the name or the email

  Scenario Outline: Le téléphone accepte 7 à 20 caractères parmi chiffres, espaces et `+ ( ) -` ; la date de naissance est une date réelle, pas dans le futur ; un champ vide efface la valeur ; une valeur invalide donne `invalid_input` avec le message du champ. (valeur acceptée : <case>)
    When the patient saves the phone "<phone>" and the birth date "<birth_date>"
    Then the patient has the phone "<saved_phone>" and the birth date "<saved_birth_date>"

    Examples:
      | case | phone | birth_date | saved_phone | saved_birth_date |
      | valeurs valides | +33 (0)6 11-22-33 | 1985-02-28 | +33 (0)6 11-22-33 | 1985-02-28 |
      | 7 caractères | 1234567 | 1990-05-17 | 1234567 | 1990-05-17 |
      | 20 caractères | 01234567890123456789 | 1990-05-17 | 01234567890123456789 | 1990-05-17 |
      | née aujourd'hui | 0601020304 | 2026-11-20 | 0601020304 | 2026-11-20 |
      | champs vides | none | none | none | none |

  Scenario Outline: Le téléphone accepte 7 à 20 caractères parmi chiffres, espaces et `+ ( ) -` ; la date de naissance est une date réelle, pas dans le futur ; un champ vide efface la valeur ; une valeur invalide donne `invalid_input` avec le message du champ. (valeur refusée : <case>)
    When the patient saves the phone "<phone>" and the birth date "<birth_date>"
    Then the change is refused as invalid on "<field>" with its message
    And the patient has the phone "0601020304" and the birth date "1990-05-17"
    And nothing is audited

    Examples:
      | case | phone | birth_date | field |
      | téléphone trop court | 12 | 1990-05-17 | phone |
      | téléphone avec des lettres | abc1234 | 1990-05-17 | phone |
      | téléphone de 21 caractères | 012345678901234567890 | 1990-05-17 | phone |
      | naissance demain | 0601020304 | 2026-11-21 | birth_date |
      | date qui n'existe pas | 0601020304 | 2026-02-30 | birth_date |

  Scenario: La modification laisse une entrée d'audit avec le nom des champs changés, jamais leurs valeurs.
    When the patient saves the phone "none" and the birth date "1990-05-17"
    Then the audit entry "user.profile_updated" by the patient names only the changed fields "phone"
    And no audit entry holds the old or new values

  Scenario: La modification laisse une entrée d'audit avec le nom des champs changés, jamais leurs valeurs. (sans changement)
    When the patient saves the phone "0601020304" and the birth date "1990-05-17"
    Then nothing is audited
