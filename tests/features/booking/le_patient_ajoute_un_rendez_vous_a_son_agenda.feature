Feature: Le patient ajoute un rendez-vous à son agenda
  En tant que patient connecté, avec ou sans mot de passe
  Je veux télécharger un RDV en fichier calendrier
  Afin qu'il apparaisse dans mon agenda personnel

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And the agenda names the clinicians, the type and the rooms
    And a signed-in patient

  Scenario Outline: Chaque RDV de la liste, à venir ou passé, se télécharge en événement iCalendar (`.ics`) aux heures de début et de fin du RDV. (<case>)
    Given the patient has a "<status>" appointment with "A" at "<start>" in room "R1"
    When the patient opens their appointments page
    Then the appointment is listed under "<list>" with its calendar file
    When the patient downloads the calendar file of the appointment
    Then the event runs from "<dtstart>" to "<dtend>"

    Examples:
      | case    | status    | start            | list    | dtstart          | dtend            |
      | à venir | BOOKED    | 2026-11-25 09:00 | À venir | 20261125T090000Z | 20261125T093000Z |
      | passé   | COMPLETED | 2026-11-18 14:00 | Passés  | 20261118T140000Z | 20261118T143000Z |
      | annulé  | CANCELLED | 2026-11-26 09:00 | Passés  | 20261126T090000Z | 20261126T093000Z |

  Scenario: Un patient ne télécharge que ses propres RDV.
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-25 09:00" in room "R1"
    And the appointment belongs to another patient
    When the patient downloads the calendar file of the appointment
    Then the download is refused with 403

  Scenario: Un patient ne télécharge que ses propres RDV. (sans session)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-25 09:00" in room "R1"
    When someone without a session downloads the calendar file of the appointment
    Then they are sent to the sign-in page
