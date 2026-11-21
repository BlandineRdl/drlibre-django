Feature: Le praticien voit son agenda du jour
  En tant que praticien
  Je veux voir les RDV d'une journée de mon agenda
  Afin que j'organise ma journée

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And the agenda names the type "Consultation" coloured "#336699" and each room
    And a signed-in patient
    And a patient "Marie Curie"
    And a patient "Paul Valéry"
    And the signed-in clinician is "A"

  Scenario: L'agenda s'ouvre sur aujourd'hui ; les liens précédent, suivant et aujourd'hui changent de jour ; une date inutilisable dans l'adresse revient à aujourd'hui. (sans jour demandé)
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And "Paul Valéry" has a "BOOKED" appointment with "A" at "2026-11-21 09:00" in room "R1"
    When the clinician opens their day
    Then the day shown is "2026-11-20" in the zone "Europe/Paris"
    And the day lists the appointments at "2026-11-20 14:00"

  Scenario: L'agenda s'ouvre sur aujourd'hui ; les liens précédent, suivant et aujourd'hui changent de jour ; une date inutilisable dans l'adresse revient à aujourd'hui. (jour demandé)
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And "Paul Valéry" has a "BOOKED" appointment with "A" at "2026-11-21 09:00" in room "R1"
    When the clinician opens the day "2026-11-21"
    Then the day shown is "2026-11-21" in the zone "Europe/Paris"
    And the day lists the appointments at "2026-11-21 09:00"

  Scenario: Les indicateurs montrent le nombre de RDV, les annulés comptés à part, les terminés, les absents et le prochain créneau libre.
    Given "Marie Curie" has a "COMPLETED" appointment with "A" at "2026-11-20 08:00" in room "R1"
    And "Paul Valéry" has a "NO_SHOW" appointment with "A" at "2026-11-20 09:00" in room "R2"
    And "Marie Curie" has a "CHECKED_IN" appointment with "A" at "2026-11-20 09:30" in room "R2"
    And "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And "Paul Valéry" has a "CANCELLED" appointment with "A" at "2026-11-20 14:30" in room "R1"
    And "A" has a stored free slot at "2026-11-20 09:00"
    And "A" has a stored free slot at "2026-11-20 10:30"
    And "A" has a stored free slot at "2026-11-20 11:00"
    And a visitor holds the slot of "A" at "2026-11-20 10:30"
    When the clinician opens their day
    Then the day counts 4 appointments, 1 cancelled, 1 completed and 1 absent
    And the next free slot is "2026-11-20 11:00"

  Scenario: Les indicateurs montrent le nombre de RDV, les annulés comptés à part, les terminés, les absents et le prochain créneau libre. (jour à venir)
    Given "A" has a stored free slot at "2026-11-20 11:00"
    And "A" has a stored free slot at "2026-11-22 08:00"
    When the clinician opens the day "2026-11-22"
    Then the day counts 0 appointments, 0 cancelled, 0 completed and 0 absent
    And the next free slot is "2026-11-22 08:00"

  Scenario: Les indicateurs montrent le nombre de RDV, les annulés comptés à part, les terminés, les absents et le prochain créneau libre. (aucun créneau libre)
    Given "B" has a stored free slot at "2026-11-20 11:00"
    When the clinician opens their day
    Then there is no next free slot

  Scenario: Les RDV sont groupés par heure, chacun avec patient, type, salle et statut.
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-20 13:00" in room "R1"
    And "Paul Valéry" has a "CHECKED_IN" appointment with "A" at "2026-11-20 13:30" in room "R2"
    And "Marie Curie" has a "COMPLETED" appointment with "A" at "2026-11-20 08:00" in room "R1"
    When the clinician opens their day
    Then the day groups them under the hours "9, 14"
    And the hour 14 shows "Marie Curie" for "Consultation" in room "R1" as "BOOKED"
    And the hour 14 shows "Paul Valéry" for "Consultation" in room "R2" as "CHECKED_IN"
    And the hour 9 shows "Marie Curie" for "Consultation" in room "R1" as "COMPLETED"

  Scenario: Seuls les RDV du praticien connecté apparaissent ; `GET /appointments` ne lui renvoie que les siens. (agenda du jour)
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And "Paul Valéry" has a "BOOKED" appointment with "B" at "2026-11-20 14:00" in room "R2"
    When the clinician opens their day
    Then every shown appointment is with "A"

  Scenario: Seuls les RDV du praticien connecté apparaissent ; `GET /appointments` ne lui renvoie que les siens. (liste des RDV)
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And the appointment holds the notes "Tension normale"
    And "Paul Valéry" has a "BOOKED" appointment with "B" at "2026-11-20 14:00" in room "R2"
    When the clinician lists their appointments
    Then every shown appointment is with "A"
    And no listed appointment carries its notes

  Scenario: Seuls les RDV du praticien connecté apparaissent ; `GET /appointments` ne lui renvoie que les siens. (sans profil praticien)
    Given the signed-in user holds no clinician profile
    When the clinician opens their day
    Then the reading is refused as "forbidden"

  Scenario: Les heures sont affichées dans le fuseau de l'hôpital, et la page indique ce fuseau.
    Given "Marie Curie" has a "BOOKED" appointment with "A" at "2026-11-19 23:30" in room "R1"
    And "Paul Valéry" has a "BOOKED" appointment with "A" at "2026-11-20 23:30" in room "R1"
    When the clinician opens the day "2026-11-20"
    Then the day shown is "2026-11-20" in the zone "Europe/Paris"
    And the day lists the appointments at "2026-11-19 23:30"
    And the day groups them under the hours "0"
