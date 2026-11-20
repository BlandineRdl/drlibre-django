Feature: Le praticien déclare ses absences
  En tant que praticien
  Je veux lister, créer et supprimer mes absences
  Afin que les périodes où je ne consulte pas soient connues

  Background:
    Given a hospital of time zone "Europe/Paris" with a department
    And the clinicians "Dr A" and "Dr B" in that department
    And an active appointment type of 30 minutes in that department
    And today is "2026-11-20"

  Scenario: Une absence porte un début, une fin après le début et un motif facultatif de 200 caractères au plus (avec motif)
    When "Dr A" records a time off from "2026-12-01T09:00" to "2026-12-01T12:00" because "Formation"
    Then "Dr A" has the time off "2026-12-01T09:00 → 2026-12-01T12:00"

  Scenario: Une absence porte un début, une fin après le début et un motif facultatif de 200 caractères au plus (sans motif)
    When "Dr A" records a time off from "2026-12-01T09:00" to "2026-12-01T12:00"
    Then "Dr A" has the time off "2026-12-01T09:00 → 2026-12-01T12:00"

  Scenario Outline: Une absence porte un début, une fin après le début et un motif facultatif de 200 caractères au plus (<case>)
    When "Dr A" records a time off from "<start>" to "<end>"
    Then the write is refused as invalid on "<field>"
    And "Dr A" has no time off

    Examples:
      | case               | start            | end              | field |
      | début mal formé    | demain           | 2026-12-01T12:00 | start |
      | fin avant le début | 2026-12-01T12:00 | 2026-12-01T09:00 | end   |
      | fin égale au début | 2026-12-01T09:00 | 2026-12-01T09:00 | end   |

  Scenario: Une absence porte un début, une fin après le début et un motif facultatif de 200 caractères au plus (motif de 201 caractères)
    When "Dr A" records a time off from "2026-12-01T09:00" to "2026-12-01T12:00" with a reason of 201 characters
    Then the write is refused as invalid on "reason"
    And "Dr A" has no time off

  Scenario: Début et fin sont saisis et affichés en heure locale de l'hôpital du praticien, et la page nomme ce fuseau (saisie en heure locale)
    Given "Dr A" saved a rule on weekday "2" from "09:00" to "12:00" every "60" minutes
    When "Dr A" records a time off from "2026-12-01T09:00" to "2026-12-01T10:00"
    Then the time off of "Dr A" starts at "2026-12-01T08:00:00+00:00"
    And the stored slots of "Dr A" on "2026-12-01" start at "10:00, 11:00" local time

  Scenario: Une période identique à une absence déjà enregistrée est refusée
    Given "Dr A" recorded a time off from "2026-12-01T09:00" to "2026-12-01T12:00"
    When "Dr A" records a time off from "2026-12-01T09:00" to "2026-12-01T12:00"
    Then the write is refused as invalid on "start"
    And "Dr A" has the time off "2026-12-01T09:00 → 2026-12-01T12:00"

  Scenario: Une période identique à une absence déjà enregistrée est refusée (période qui chevauche sans être identique)
    Given "Dr A" recorded a time off from "2026-12-01T09:00" to "2026-12-01T12:00"
    When "Dr A" records a time off from "2026-12-01T10:00" to "2026-12-01T12:00"
    Then "Dr A" has the time off "2026-12-01T09:00 → 2026-12-01T12:00, 2026-12-01T10:00 → 2026-12-01T12:00"

  Scenario: Une absence n'annule pas les RDV déjà pris pendant sa période
    Given "Dr A" has a "BOOKED" appointment from "2026-12-01T09:00" to "2026-12-01T09:30"
    When "Dr A" records a time off from "2026-12-01T08:00" to "2026-12-01T12:00"
    Then the appointment of "Dr A" is still "BOOKED"

  Scenario: Le praticien ne voit et ne modifie que ses propres absences (liste)
    Given "Dr A" recorded a time off from "2026-12-01T09:00" to "2026-12-01T12:00"
    And "Dr B" recorded a time off from "2026-12-02T09:00" to "2026-12-02T12:00"
    Then "Dr A" has the time off "2026-12-01T09:00 → 2026-12-01T12:00"

  Scenario: Le praticien ne voit et ne modifie que ses propres absences (suppression refusée)
    Given "Dr B" recorded a time off from "2026-12-02T09:00" to "2026-12-02T12:00"
    When "Dr A" deletes the time off of "Dr B"
    Then the write is refused as "forbidden"
    And "Dr B" has the time off "2026-12-02T09:00 → 2026-12-02T12:00"

  Scenario: Chaque écriture laisse une entrée d'audit sans donnée personnelle
    When "Dr A" records a time off from "2026-12-01T09:00" to "2026-12-01T12:00" because "Rendez-vous médical personnel"
    And "Dr A" deletes that time off
    Then the audit holds "time_off.created, time_off.deleted" by "Dr A"
    And no audit entry mentions "Rendez-vous médical personnel"

  Scenario: Règle §4 : si l'entrée d'audit ne peut pas être écrite, l'écriture n'a pas lieu (absence)
    Given "Dr A" saved a rule on weekday "2" from "09:00" to "12:00" every "60" minutes
    And the audit log is unavailable
    When "Dr A" records a time off from "2026-12-01T09:00" to "2026-12-01T12:00"
    Then "Dr A" has no time off
    And the stored slots of "Dr A" are unchanged
