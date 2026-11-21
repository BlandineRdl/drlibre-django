Feature: L'admin voit le résumé hebdomadaire des disponibilités
  En tant que admin
  Je veux voir dans la liste des praticiens un résumé de leurs plages hebdomadaires
  Afin que je contrôle d'un coup d'œil qui consulte et quand

  Background:
    Given a hospital of time zone "America/Montreal" with the clinicians "Dr A" and "Dr B"
    And today is "2026-11-20"
    And the admin is signed in on the console

  Scenario: La liste des praticiens montre, pour chacun, le résumé de ses plages hebdomadaires, en heure locale de son hôpital
    Given "Dr A" saved a rule on weekday "2" from "14:00" to "17:00"
    And "Dr A" saved a rule on weekday "1" from "09:00" to "12:00"
    And "Dr A" saved a rule on weekday "1" from "13:00" to "15:00"
    When the admin opens the clinicians list
    Then the summary of "Dr A" reads "Lun 09:00-12:00, 13:00-15:00 · Mar 14:00-17:00"
    And the summary of "Dr B" reads "Aucune plage"

  Scenario: Le résumé reflète une plage créée, modifiée ou supprimée dès son enregistrement (création)
    Given the admin opened the clinicians list
    When "Dr A" saves a rule on weekday "3" from "08:00" to "10:00"
    And the admin opens the clinicians list
    Then the summary of "Dr A" reads "Mer 08:00-10:00"

  Scenario: Le résumé reflète une plage créée, modifiée ou supprimée dès son enregistrement (modification)
    Given "Dr A" saved a rule on weekday "3" from "08:00" to "10:00"
    When "Dr A" moves that rule to weekday "4" from "10:00" to "12:00"
    And the admin opens the clinicians list
    Then the summary of "Dr A" reads "Jeu 10:00-12:00"

  Scenario: Le résumé reflète une plage créée, modifiée ou supprimée dès son enregistrement (suppression)
    Given "Dr A" saved a rule on weekday "3" from "08:00" to "10:00"
    When "Dr A" deletes that rule
    And the admin opens the clinicians list
    Then the summary of "Dr A" reads "Aucune plage"
