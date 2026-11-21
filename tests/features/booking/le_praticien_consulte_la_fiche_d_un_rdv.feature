Feature: Le praticien consulte la fiche d'un RDV
  En tant que praticien
  Je veux ouvrir un de mes RDV depuis l'agenda
  Afin que j'aie sous les yeux le patient, le RDV et son historique

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And the agenda names the type "Consultation" coloured "#336699" and each room
    And a signed-in patient
    And the signed-in clinician is "A"

  Scenario: La fiche montre le nom, le téléphone et l'âge du patient, l'heure, le type, la salle, le motif et le statut.
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And the appointment holds the notes "Tension normale"
    When the clinician opens the appointment
    Then the file shows "Patient Test", phone "0600000000", age 46, "Consultation" in room "R1", the reason and the status "BOOKED"
    And the file shows the notes "Tension normale" and offers "check_in, no_show, cancel, reschedule"

  Scenario: L'historique liste les entrées d'audit de ce RDV dans l'ordre chronologique.
    Given the patient has a "BOOKED" appointment with "A" at "2026-11-20 14:00" in room "R1"
    And the audit holds "booking.appointment_status_changed" on the appointment by the clinician at "2026-11-20 14:05"
    And the audit holds "booking.appointment_booked" on the appointment by the patient at "2026-11-18 09:00"
    And the audit holds "booking.appointment_rescheduled" on the appointment by the staff at "2026-11-19 09:00"
    When the clinician opens the appointment
    Then the history lists "booking.appointment_booked by PATIENT; booking.appointment_rescheduled by STAFF; booking.appointment_status_changed by CLINICIAN"

  Scenario: Le RDV d'un autre praticien affiche « Not your appointment » et aucune de ses données.
    Given the patient has a "BOOKED" appointment with "B" at "2026-11-20 14:00" in room "R2"
    When the clinician opens the appointment
    Then the reading is refused as "forbidden"

  Scenario: Un RDV inexistant donne `not_found`.
    When the clinician opens an unknown appointment
    Then the reading is refused as "not_found"
