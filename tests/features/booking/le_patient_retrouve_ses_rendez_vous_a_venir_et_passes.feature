Feature: Le patient retrouve ses rendez-vous à venir et passés
  En tant que patient connecté, avec ou sans mot de passe
  Je veux voir tous mes RDV, à venir et passés
  Afin que je sache avec qui, quand et où j'ai rendez-vous

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" with default room "R2" in that department
    And the agenda names the clinicians, the type and the rooms
    And a signed-in patient

  Scenario: À venir : RDV `BOOKED` ou `CHECKED_IN` pas encore commencés, du plus proche au plus lointain. Passés : tous les autres, du plus récent au plus ancien.
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-25 09:00" in room "R1"
    And the patient has a "CHECKED_IN" appointment with "B" at "2026-11-22 10:00" in room "R2"
    And the patient has a "BOOKED" appointment with "A" at "2026-11-20 09:30" in room "R1"
    And the patient has a "COMPLETED" appointment with "A" at "2026-11-18 09:00" in room "R1"
    And the patient has a "CANCELLED" appointment with "B" at "2026-11-26 09:00" in room "R2"
    And the patient has a "NO_SHOW" appointment with "B" at "2026-11-19 09:00" in room "R2"
    When the patient lists their appointments
    Then the upcoming appointments start at "2026-11-22 10:00, 2026-11-25 09:00"
    And the past appointments start at "2026-11-26 09:00, 2026-11-20 09:30, 2026-11-19 09:00, 2026-11-18 09:00"

  Scenario: Chaque RDV montre le praticien (nom, titre, spécialité), la date, l'heure de début et de fin dans le fuseau de l'hôpital, qui est nommé, l'hôpital (nom, adresse), le département, la salle quand elle est attribuée, le type, le statut et le motif.
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-25 09:00" in room "R1"
    When the patient lists their appointments
    Then the listed appointment shows every field, in room "R1"

  Scenario: Chaque RDV montre le praticien (nom, titre, spécialité), la date, l'heure de début et de fin dans le fuseau de l'hôpital, qui est nommé, l'hôpital (nom, adresse), le département, la salle quand elle est attribuée, le type, le statut et le motif. (sans salle)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-25 09:00" in no room
    When the patient lists their appointments
    Then the listed appointment shows every field, in no room

  Scenario: Un RDV réservé par le parcours sans compte apparaît dès la session ouverte.
    Given "A" is free every 30 minutes from "2026-11-23 09:00" for 1 slots
    And the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the API lists the new appointment at "2026-11-23 09:00" as upcoming with the opened session

  Scenario Outline: `GET /appointments` filtre par praticien, statut et période, et ne renvoie au patient que ses propres RDV, même s'il nomme un autre patient. (<case>)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-25 09:00" in room "R1"
    And the patient has a "CANCELLED" appointment with "A" at "2026-11-26 09:00" in room "R1"
    And the patient has a "BOOKED" appointment with "B" at "2026-11-27 09:00" in room "R2"
    And the patient has a "BOOKED" appointment with "A" at "2026-12-10 09:00" in room "R1"
    And another patient has a "BOOKED" appointment with "A" at "2026-11-28 09:00"
    When the patient asks the API for "<query>"
    Then the API lists the patient's appointments at "<starts>"

    Examples:
      | case | query | starts |
      | sans filtre | none | 2026-11-25 09:00, 2026-11-27 09:00, 2026-12-10 09:00, 2026-11-26 09:00 |
      | par praticien | clinician=B | 2026-11-27 09:00 |
      | par statut | status=CANCELLED | 2026-11-26 09:00 |
      | par période | from=2026-11-26T00:00:00Z&to=2026-12-01T00:00:00Z | 2026-11-27 09:00, 2026-11-26 09:00 |
      | tout à la fois | clinician=A&status=BOOKED&from=2026-11-24T00:00:00Z&to=2026-12-01T00:00:00Z | 2026-11-25 09:00 |
      | en nommant un autre patient | patient=other | 2026-11-25 09:00, 2026-11-27 09:00, 2026-12-10 09:00, 2026-11-26 09:00 |
