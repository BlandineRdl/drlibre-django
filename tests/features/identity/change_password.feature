Feature: Un utilisateur change son mot de passe
  En tant qu'utilisateur qui a un mot de passe (admin, praticien ou patient créé par un admin)
  Je veux changer mon mot de passe
  Afin que le mot de passe temporaire donné par l'admin ne reste pas en usage

  Background:
    Given a CLINICIAN "clinician@example.org" created by an admin with password "temporary-pass-1"

  Scenario: Le changement exige le mot de passe actuel et un nouveau, qui remplace le temporaire
    When "clinician@example.org" changes password from "temporary-pass-1" to "my-own-password"
    Then "clinician@example.org" no longer has to change password
    And "clinician@example.org" can sign in with "my-own-password"

  Scenario Outline: Le changement exige le mot de passe actuel et un nouveau, différent, de 10 à 72 caractères (<case>)
    When "clinician@example.org" changes password from "<current>" to "<new>"
    Then the change is refused as invalid on "<field>"
    And "clinician@example.org" still has to change password
    And nothing is audited

    Examples:
      | case                     | current          | new                                                                       | field            |
      | mot de passe actuel faux | wrong-password-1 | my-own-password                                                           | current_password |
      | nouveau identique        | temporary-pass-1 | temporary-pass-1                                                          | new_password     |
      | 9 caractères             | temporary-pass-1 | ninechars                                                                 | new_password     |
      | 73 caractères            | temporary-pass-1 | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | new_password     |

  Scenario: Après une connexion avec un mot de passe temporaire, l'utilisateur doit le changer avant d'accéder à son espace
    When "clinician@example.org" signs in on the sign-in page with "temporary-pass-1"
    Then the page "/workspace/" sends them to "/account/password"
    When they choose the new password "my-own-password" on the password page
    Then the page "/workspace/" opens

  Scenario: Un patient sans mot de passe ne voit pas cette action
    Given a passwordless PATIENT "patient@example.org" with an open session
    Then the page "/portal/" shows no link to "/account/password"
    And the page "/account/password" is forbidden
    When "patient@example.org" changes password from "anything-12" to "my-own-password"
    Then the change is refused as "forbidden"

  Scenario: Le changement est audité, sans le mot de passe
    When "clinician@example.org" changes password from "temporary-pass-1" to "my-own-password"
    Then the audit holds "user.password_changed" without metadata
