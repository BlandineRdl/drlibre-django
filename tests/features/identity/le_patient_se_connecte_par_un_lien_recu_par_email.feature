Feature: Le patient se connecte par un lien reçu par email
  En tant que patient
  Je veux recevoir un lien de connexion par email, sans mot de passe
  Afin de retrouver mon espace patient après ma réservation

  Background:
    Given an active passwordless patient "lea@example.org"

  Scenario: Sur la page de connexion, le patient saisit son email et demande un lien ; la page affiche le même message que l'adresse ait un compte ou non (adresse connue)
    When "lea@example.org" asks for a link on the sign-in page
    Then the page says a link was sent if the address has a patient account

  Scenario: Sur la page de connexion, le patient saisit son email et demande un lien ; la page affiche le même message que l'adresse ait un compte ou non (adresse inconnue)
    When "inconnu@example.org" asks for a link on the sign-in page
    Then the page says a link was sent if the address has a patient account

  Scenario: Sur la page de connexion, le patient saisit son email et demande un lien ; la page affiche le même message que l'adresse ait un compte ou non (pages identiques)
    When "lea@example.org" asks for a link on the sign-in page
    And "inconnu@example.org" asks for a link on the sign-in page
    Then both answers are the same page

  Scenario Outline: Le lien n'est envoyé qu'à un patient actif ; un email inconnu, d'admin, de praticien ou d'utilisateur inactif ne reçoit rien et ne crée rien (<case>)
    Given <setup>
    When "autre@example.org" asks for a link on the sign-in page
    Then no email was sent
    And no link and no account were created

    Examples:
      | case                           | setup                                    |
      | un email inconnu               | no other account                         |
      | un email d'admin               | an active ADMIN account "autre@example.org" |
      | un email de praticien          | an active CLINICIAN account "autre@example.org" |
      | un email d'utilisateur inactif | an inactive PATIENT account "autre@example.org" |

  Scenario: Le lien vaut 15 minutes (encore valable à 14 minutes)
    Given "lea@example.org" asked for a link
    When 14 minutes pass
    And the patient opens the link and presses "Continuer"
    Then the patient lands on "/portal/"

  Scenario: Le lien vaut 15 minutes (refusé à 15 minutes)
    Given "lea@example.org" asked for a link
    When 15 minutes pass
    And the patient opens the link and presses "Continuer"
    Then no session was opened

  Scenario: Le lien sert une fois
    Given "lea@example.org" asked for a link
    And the patient opens the link and presses "Continuer"
    When the patient opens the link and presses "Continuer"
    Then only one session exists

  Scenario: En demander un nouveau annule les précédents
    Given "lea@example.org" asked for a link
    And "lea@example.org" asked for a link
    When the patient opens the first link and presses "Continuer"
    Then no session was opened

  Scenario: Au plus 3 liens par heure et par email
    Given "lea@example.org" asked for a link 3 times
    When "lea@example.org" asks for a link on the sign-in page
    Then 3 link emails were sent in all
    And the page says a link was sent if the address has a patient account

  Scenario: Au plus 3 liens par heure et par email (de nouveau permis après une heure)
    Given "lea@example.org" asked for a link 3 times
    And 61 minutes pass
    When "lea@example.org" asks for a link on the sign-in page
    Then 4 link emails were sent in all

  Scenario: 20 demandes par heure et par adresse réseau
    Given 20 requests for distinct patients from the network "10.0.0.7"
    When "lea@example.org" asks for a link from the network "10.0.0.7"
    Then 20 link emails were sent in all
    And the page says a link was sent if the address has a patient account

  Scenario: Ouvrir le lien affiche un bouton « Continuer » ; le lien n'est consommé qu'au clic (ouverture seule)
    Given "lea@example.org" asked for a link
    When the patient opens the link
    Then the page offers a "Continuer" button
    And the link is still usable

  Scenario: Ouvrir le lien affiche un bouton « Continuer » ; le lien n'est consommé qu'au clic, puis le patient arrive dans son espace sur une adresse sans le jeton
    Given "lea@example.org" asked for a link
    When the patient opens the link and presses "Continuer"
    Then the patient lands on "/portal/"
    And the address holds no token

  Scenario Outline: La session dure 24 h et n'est jamais prolongée, que le patient ait un mot de passe ou non (<case>)
    Given a patient "<email>" <password>
    And "<email>" asked for a link
    When the patient opens the link and presses "Continuer"
    And 13 hours pass and the patient visits their session
    Then the session still ends 24 hours after the sign-in

    Examples:
      | case                     | email           | password          |
      | patient sans mot de passe | sans@example.org | without a password |
      | patient avec mot de passe | avec@example.org | with a password    |

  Scenario Outline: Un lien expiré, déjà utilisé ou annulé ne connecte pas (<case>)
    Given "lea@example.org" asked for a link
    And the link is <state>
    When the patient opens the link and presses "Continuer"
    Then no session was opened
    And the page offers to request a new link

    Examples:
      | case             | state     |
      | lien expiré      | expired   |
      | lien déjà utilisé | used      |
      | lien annulé      | cancelled |

  Scenario: L'email du lien est le seul email qui contient un lien qui connecte ; le jeton n'apparaît jamais dans les journaux
    Given "lea@example.org" asked for a link
    When the patient opens the link and presses "Continuer"
    Then only the link email holds a link that signs in
    And the logs hold no token

  Scenario: Lien demandé, lien utilisé et lien refusé sont audités avec le domaine de l'email seulement (demandé)
    When "lea@example.org" asks for a link on the sign-in page
    Then the audit holds one "identity.link_requested" entry with only the email domain

  Scenario: Lien demandé, lien utilisé et lien refusé sont audités avec le domaine de l'email seulement (utilisé)
    Given "lea@example.org" asked for a link
    When the patient opens the link and presses "Continuer"
    Then the audit holds one "identity.link_used" entry with only the email domain

  Scenario: Lien demandé, lien utilisé et lien refusé sont audités avec le domaine de l'email seulement (refusé)
    Given "lea@example.org" asked for a link
    And the link is used
    When the patient opens the link and presses "Continuer"
    Then the audit holds one "identity.link_refused" entry with only the email domain

  Scenario: `POST /auth/link` répond toujours de la même façon (adresse connue ou non)
    When the API is asked for a link for "lea@example.org" and for "inconnu@example.org"
    Then both API answers are identical with status 202

  Scenario: `POST /auth/link` répond toujours de la même façon (limite dépassée)
    Given "lea@example.org" asked for a link 3 times
    When the API is asked for a link for "lea@example.org" and for "inconnu@example.org"
    Then both API answers are identical with status 202
    And 3 link emails were sent in all

  Scenario: `POST /auth/link/verify` échange le jeton contre la session
    Given "lea@example.org" asked for a link
    When the API verifies the link token
    Then the API answer is 200 with a 24 hour session cookie
