Feature: Le praticien gère ses plages hebdomadaires
  En tant que praticien
  Je veux lister, créer, modifier et supprimer mes plages hebdomadaires
  Afin que mes disponibilités récurrentes soient publiées

  Background:
    Given a hospital of time zone "Europe/Paris" with a department
    And the clinicians "Dr A" and "Dr B" in that department
    And an active appointment type of 30 minutes in that department
    And today is "2026-11-20"

  Scenario: Une plage porte un jour de la semaine, une heure de début et une heure de fin (HH:MM, fin après début), un pas de 5 à 240 minutes et une salle facultative (sans salle)
    When "Dr A" saves a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    Then "Dr A" has the rules "Lundi 09:00-12:00"
    And the rule of "Dr A" has a 15-minute step and no room

  Scenario Outline: Une plage porte un jour de la semaine, une heure de début et une heure de fin (HH:MM, fin après début), un pas de 5 à 240 minutes et une salle facultative (<case>)
    When "Dr A" saves a rule on weekday "<weekday>" from "<start>" to "<end>" every "<step>" minutes
    Then the write is refused as invalid on "<field>"
    And "Dr A" has no rule

    Examples:
      | case                 | weekday | start | end   | step | field        |
      | heure mal formée     | 1       | 9h    | 12:00 | 15   | start        |
      | fin avant le début   | 1       | 12:00 | 09:00 | 15   | end          |
      | fin égale au début   | 1       | 09:00 | 09:00 | 15   | end          |
      | pas sous 5 minutes   | 1       | 09:00 | 12:00 | 4    | step_minutes |
      | pas au-delà de 240   | 1       | 09:00 | 12:00 | 241  | step_minutes |
      | jour inconnu         | 7       | 09:00 | 12:00 | 15   | weekday      |

  Scenario: Les heures sont saisies et affichées en heure locale de l'hôpital du praticien, et la page nomme ce fuseau (saisie en heure locale)
    When "Dr A" saves a rule on weekday "2" from "09:00" to "10:00" every "30" minutes
    Then the stored slots of "Dr A" on "2026-11-24" start at "09:00, 09:30" local time

  Scenario: Les heures sont saisies et affichées en heure locale de l'hôpital du praticien, et la page nomme ce fuseau (la page nomme ce fuseau)
    Given "Dr A" saved a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    When "Dr A" opens the page "/workspace/availability/"
    Then the page names the time zone "Europe/Paris"
    And the page shows "09:00-12:00"

  Scenario: Les heures sont saisies et affichées en heure locale de l'hôpital du praticien, et la page nomme ce fuseau (le formulaire nomme ce fuseau)
    When "Dr A" opens the page "/workspace/availability/new"
    Then the page names the time zone "Europe/Paris"

  Scenario: La salle, si elle est donnée, est une salle active du département du praticien (salle acceptée)
    Given an active room "R1" in that department
    When "Dr A" saves a rule on weekday "1" from "09:00" to "12:00" every "15" minutes in room "R1"
    Then the rule of "Dr A" is in room "R1"

  Scenario Outline: La salle, si elle est donnée, est une salle active du département du praticien (<case>)
    Given <room>
    When "Dr A" saves a rule on weekday "1" from "09:00" to "12:00" every "15" minutes in room "R9"
    Then the write is refused as invalid on "room_id"
    And "Dr A" has no rule

    Examples:
      | case                     | room                                      |
      | salle inactive           | an inactive room "R9" in that department  |
      | salle d'un autre service | an active room "R9" in another department |
      | salle inconnue           | an unknown room "R9"                      |

  Scenario: Deux plages du même jour peuvent se toucher mais pas se chevaucher ; le refus le dit (plages qui se touchent)
    Given "Dr A" saved a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    When "Dr A" saves a rule on weekday "1" from "12:00" to "14:00" every "15" minutes
    Then "Dr A" has the rules "Lundi 09:00-12:00, Lundi 12:00-14:00"

  Scenario: Deux plages du même jour peuvent se toucher mais pas se chevaucher ; le refus le dit (chevauchement refusé)
    Given "Dr A" saved a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    When "Dr A" saves a rule on weekday "1" from "11:00" to "13:00" every "15" minutes
    Then the write is refused as invalid on "start" naming "Lundi 09:00-12:00"
    And "Dr A" has the rules "Lundi 09:00-12:00"

  Scenario: Deux plages du même jour peuvent se toucher mais pas se chevaucher ; le refus le dit (une plage modifiée ne se chevauche pas elle-même)
    Given "Dr A" saved a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    When "Dr A" edits that rule to weekday "1" from "08:00" to "13:00" every "15" minutes
    Then "Dr A" has the rules "Lundi 08:00-13:00"

  Scenario: Une nouvelle plage est valable dès aujourd'hui, sans date de fin
    When "Dr A" saves a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    Then the rule of "Dr A" is valid from "2026-11-20" with no end date

  Scenario: Une nouvelle plage est valable dès aujourd'hui, sans date de fin (la modification garde sa date de début)
    Given "Dr A" saved a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    And today is "2026-12-03"
    When "Dr A" edits that rule to weekday "1" from "10:00" to "12:00" every "15" minutes
    Then the rule of "Dr A" is valid from "2026-11-20" with no end date

  Scenario: La suppression demande une confirmation
    Given "Dr A" saved a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    When "Dr A" opens the deletion of that rule
    Then the page asks for confirmation
    And "Dr A" has the rules "Lundi 09:00-12:00"
    When "Dr A" confirms the deletion
    Then "Dr A" has no rule

  Scenario: Le praticien ne voit et ne modifie que ses propres plages (liste)
    Given "Dr A" saved a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    And "Dr B" saved a rule on weekday "2" from "14:00" to "18:00" every "15" minutes
    Then "Dr A" has the rules "Lundi 09:00-12:00"

  Scenario: Le praticien ne voit et ne modifie que ses propres plages (modification refusée)
    Given "Dr B" saved a rule on weekday "2" from "14:00" to "18:00" every "15" minutes
    When "Dr A" edits the rule of "Dr B" to weekday "2" from "08:00" to "18:00" every "15" minutes
    Then the write is refused as "forbidden"
    And "Dr B" has the rules "Mardi 14:00-18:00"

  Scenario: Le praticien ne voit et ne modifie que ses propres plages (suppression refusée)
    Given "Dr B" saved a rule on weekday "2" from "14:00" to "18:00" every "15" minutes
    When "Dr A" deletes the rule of "Dr B"
    Then the write is refused as "forbidden"
    And "Dr B" has the rules "Mardi 14:00-18:00"

  Scenario: Une salle utilisée par une plage ne peut pas être supprimée, et le refus le dit
    Given an active room "R1" in that department
    And "Dr A" saved a rule on weekday "1" from "09:00" to "12:00" every "15" minutes in room "R1"
    When the admin deletes the room "R1"
    Then the write is refused as "has_dependents" listing the availability rule "Lundi 09:00-12:00"

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle
    When "Dr A" saves a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    And "Dr A" edits that rule to weekday "1" from "09:00" to "11:00" every "30" minutes
    And "Dr A" deletes that rule
    Then the audit holds "availability_rule.created, availability_rule.updated, availability_rule.deleted" by "Dr A"
    And the audit metadata holds only "weekday, changed"
    And the "availability_rule.updated" entry names the changed fields "end, step_minutes"

  Scenario: Règle §4 : si l'entrée d'audit ne peut pas être écrite, l'écriture n'a pas lieu (plage)
    Given "Dr A" saved a rule on weekday "1" from "09:00" to "12:00" every "15" minutes
    And the audit log is unavailable
    When "Dr A" saves a rule on weekday "2" from "09:00" to "12:00" every "15" minutes
    Then "Dr A" has the rules "Lundi 09:00-12:00"
    And the stored slots of "Dr A" are unchanged

  Scenario: Règle §4 : un enregistrement absent donne not_found (plage)
    When "Dr A" deletes an unknown rule
    Then the write is refused as "not_found"
