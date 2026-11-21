Feature: L'admin exporte les RDV filtrés en CSV
  En tant qu'admin
  Je veux exporter en CSV tout l'ensemble filtré, pas seulement la page affichée
  Afin que j'analyse l'activité hors de l'application sans exposer de donnée personnelle

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And a signed-in admin
    And "A" works in "Cardiologie" at "Hôpital Nord" in "Europe/Paris"
    And "B" works in "Rythmologie" at "Hôpital du Lamentin" in "America/Martinique"
    And these appointments
      | name | clinician | start            | status    | source |
      | b1   | B         | 2026-11-20 13:00 | CANCELLED | ONLINE |
    And 25 more "BOOKED" appointments of "A" one day apart from "2026-11-22 09:00"

  Scenario: Colonnes : id du RDV, début, fin, statut, source, id patient, id praticien, id département, id type de RDV, id salle.
    When the admin exports the appointments with "clinician=A"
    Then the export holds 25 rows of the columns "id, start, end, status, source, patient_id, clinician_id, department_id, appointment_type_id, room_id"
    And each exported row carries the ids of its appointment

  Scenario: Les instants sont en UTC au format ISO 8601.
    When the admin exports the appointments with "clinician=A"
    Then every exported instant is in UTC

  Scenario: Aucun nom ni texte libre n'apparaît.
    When the admin exports the appointments with ""
    Then no exported value is a name, a reason or a cancellation reason

  Scenario Outline: Une cellule qui commence par `=`, `+`, `-` ou `@` est préfixée d'une apostrophe. (<case>)
    When a cell "<value>" is exported
    Then the exported cell reads "<cell>"

    Examples:
      | case            | value    | cell      |
      | égal            | =SUM(A1) | '=SUM(A1) |
      | plus            | +1       | '+1       |
      | moins           | -1       | '-1       |
      | arobase         | @SUM(A1) | '@SUM(A1) |
      | texte ordinaire | BOOKED   | BOOKED    |

  Scenario: L'export laisse une entrée d'audit avec le nombre de lignes.
    When the admin exports the appointments with "clinician=A"
    Then the audit entry "booking.appointments_exported" has the admin as actor and counts 25

  Scenario: Règle §10 : seul l'admin exporte les RDV
    When the patient exports every appointment
    Then the booking is refused as "forbidden"
    And the audit holds no "booking.appointments_exported"
