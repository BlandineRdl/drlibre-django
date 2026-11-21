Feature: Une suppression refusée liste les RDV et entrées d'attente qui en dépendent
  En tant qu'admin
  Je veux que la suppression d'un enregistrement encore utilisé par des RDV ou des entrées d'attente soit refusée
  Afin qu'aucun RDV ni aucune entrée d'attente ne perde son praticien, sa salle, son type ou son patient

  Background:
    Given a hospital "NORD" exists
    And a department "CARD" exists in hospital "NORD"
    And a specialty "CARDIO" exists
    And a room "R101" exists in department "CARD"
    And a room "R102" exists in department "CARD"
    And an appointment type "CONSULT" exists in department "CARD"
    And an active clinician "Ana Bel"
    And "Ana Bel" has a profile in department "CARD" with specialty "CARDIO" and default room "R102"

  Scenario: Une salle qui a des RDV ne peut pas être supprimée.
    Given the room "R101" has an appointment
    When the admin deletes the room "R101"
    Then the delete is refused listing appointment "RDV 2026-12-01"

  Scenario: Un type de RDV qui a des RDV ou des entrées d'attente ne peut pas être supprimé.
    Given the appointment type "CONSULT" has an appointment and a waitlist entry
    When the admin deletes the appointment type "CONSULT"
    Then the delete is refused listing appointment "RDV 2026-12-01" and waitlist_entry "Attente 2026-12-03"

  Scenario: Un profil praticien qui a des RDV ne peut pas être supprimé.
    Given the profile of "Ana Bel" has an appointment
    When the admin deletes the profile of "Ana Bel"
    Then the delete is refused listing appointment "RDV 2026-12-02"
    And the refusal says "Ce praticien a des rendez-vous ou une liste d'attente."

  Scenario: Un utilisateur qui a des RDV, comme patient ou comme praticien, ne peut pas être supprimé ; le message invite à le désactiver.
    Given a patient user "paul@example.org" with an appointment
    And a clinician user "ana@example.org" with an appointment
    When the admin deletes the user "paul@example.org"
    Then the delete is refused listing appointment "RDV 2026-12-04"
    And the refusal says "Désactivez ce compte plutôt que de le supprimer."
    When the admin deletes the user "ana@example.org"
    Then the delete is refused listing appointment "RDV 2026-12-04"
    And the refusal says "Désactivez ce compte plutôt que de le supprimer."

  Scenario Outline: Chaque refus renvoie `has_dependents` et liste ce qui utilise encore l'enregistrement.
    Given the room "R101" has an appointment
    And the appointment type "CONSULT" has an appointment and a waitlist entry
    And the profile of "Ana Bel" has an appointment
    And a patient user "paul@example.org" with an appointment
    When the admin deletes <record>
    Then the delete is refused listing <listing>

    Examples:
      | record                         | listing                                                              |
      | the room "R101"                | appointment "RDV 2026-12-01"                                         |
      | the appointment type "CONSULT" | appointment "RDV 2026-12-01" and waitlist_entry "Attente 2026-12-03" |
      | the profile of "Ana Bel"       | appointment "RDV 2026-12-02"                                         |
      | the user "paul@example.org"    | appointment "RDV 2026-12-04"                                         |
