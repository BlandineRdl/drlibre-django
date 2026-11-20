Feature: L'admin rattache un profil praticien
  En tant qu'admin
  Je veux rattacher un profil à un utilisateur praticien actif qui n'en a pas
  Afin qu'il soit placé dans un département, avec une spécialité et un poids round robin

  Background:
    Given a hospital "NORD" exists
    And a department "CARD" exists in hospital "NORD"
    And a department "PEDIA" exists in hospital "NORD"
    And a specialty "CARDIO" exists
    And a room "R101" exists in department "CARD"
    And an active clinician "Ana Bel"

  Scenario: Le profil porte un département, une spécialité, un titre, une bio, une salle par défaut et un poids, à 1 par défaut
    When the admin attaches a profile to "Ana Bel" in department "CARD" with specialty "CARDIO" and default room "R101"
    Then the profile of "Ana Bel" is in department "CARD" with specialty "CARDIO", default room "R101" and weight 1

  Scenario Outline: Le profil porte un département, une spécialité, un titre, une bio, une salle par défaut (salle active de ce département) et un poids d'au moins 1 (refus : <case>)
    Given a room "R201" exists in department "PEDIA"
    And an inactive room "R102" exists in department "CARD"
    When the admin attaches a profile to "Ana Bel" with <field> "<value>"
    Then the save is refused as invalid on "<field>"

    Examples:
      | case                             | field           | value |
      | salle par défaut d'un autre département | default_room_id | R201  |
      | salle par défaut inactive        | default_room_id | R102  |
      | poids nul                        | weight          | 0     |
      | spécialité inconnue              | specialty_id    | nope  |

  Scenario Outline: Le profil se rattache à un utilisateur praticien actif qui n'en a pas (<case>)
    Given <situation>
    When the admin attaches a profile to "<who>" in department "CARD" with specialty "CARDIO" and default room "R101"
    Then the save is refused as invalid on "user_id"

    Examples:
      | case             | situation                                                                                   | who     |
      | inactif          | an inactive clinician "Old Doc"                                                             | Old Doc |
      | déjà un profil   | "Ana Bel" has a profile in department "CARD" with specialty "CARDIO" and default room "R101" | Ana Bel |

  Scenario: Un département qui a des praticiens ne peut pas être supprimé
    Given "Ana Bel" has a profile in department "CARD" with specialty "CARDIO" and default room "R101"
    When the admin deletes the department "CARD"
    Then the delete is refused listing clinician "Dr Ana Bel" and room "R101"

  Scenario: Une spécialité portée par un praticien ne peut pas être supprimée
    Given "Ana Bel" has a profile in department "CARD" with specialty "CARDIO" and default room "R101"
    When the admin deletes the specialty "CARDIO"
    Then the delete is refused listing clinician "Dr Ana Bel"

  Scenario: Une salle qui est la salle par défaut d'un praticien ne peut pas être supprimée
    Given "Ana Bel" has a profile in department "CARD" with specialty "CARDIO" and default room "R101"
    When the admin deletes the room "R101"
    Then the delete is refused listing clinician "Dr Ana Bel"

  Scenario: Une salle par défaut ne peut pas changer de département tant que des praticiens de l'ancien département l'utilisent
    Given "Ana Bel" has a profile in department "CARD" with specialty "CARDIO" and default room "R101"
    When the admin moves the room "R101" to department "PEDIA"
    Then the move is refused listing clinician "Dr Ana Bel"

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle (rattachement)
    When the admin attaches a profile to "Ana Bel" in department "CARD" with specialty "CARDIO" and default room "R101"
    Then the audit holds "clinician_profile.created" holding only ids

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle (modification)
    Given "Ana Bel" has a profile in department "CARD" with specialty "CARDIO" and default room "R101"
    When the admin edits the profile of "Ana Bel" setting weight "3"
    Then the audit holds "clinician_profile.updated" holding only ids
    And the profile of "Ana Bel" has weight 3

  Scenario: Règle §10 : un profil praticien ne peut pas être supprimé tant qu'il a des rendez-vous
    Given "Ana Bel" has a profile in department "CARD" with specialty "CARDIO" and default room "R101"
    And the profile of "Ana Bel" has an appointment
    When the admin deletes the profile of "Ana Bel"
    Then the delete is refused listing appointment "RDV 2026-12-02"

  Scenario: Règle §10 : un profil praticien sans rendez-vous est supprimé après confirmation
    Given "Ana Bel" has a profile in department "CARD" with specialty "CARDIO" and default room "R101"
    And the admin is signed in on the console
    When the admin opens the deletion of the profile of "Ana Bel"
    Then the deletion asks for confirmation
    When the admin confirms the deletion
    Then "Ana Bel" has no profile
    And the audit holds "clinician_profile.deleted" holding only ids
