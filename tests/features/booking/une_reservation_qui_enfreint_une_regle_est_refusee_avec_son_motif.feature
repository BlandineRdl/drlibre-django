Feature: Une réservation qui enfreint une règle est refusée avec son motif
  En tant que visiteur
  Je veux savoir pourquoi ma réservation échoue et voir les créneaux encore libres
  Afin que je puisse en choisir un autre sans recommencer

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And an active clinician "B" in that department
    And a signed-in patient
    And "A" and "B" are free at "2026-11-23 09:00"

  Scenario: Le placement s'arrête au premier échec, dans cet ordre : type inactif, utilisateur praticien inactif ou départements différents (`not_found`) ; RDV actif qui chevauche pour le même praticien ou le même patient (`conflict`, avec les ressources en cause) ; règles de réservation (`rule_violation`, avec les règles enfreintes) ; aucune salle libre pour un type qui en exige (`no_room_available`) (type inactif)
    Given the appointment type is inactive
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "not_found"
    And nothing was written

  Scenario: Le placement s'arrête au premier échec, dans cet ordre : type inactif, utilisateur praticien inactif ou départements différents (`not_found`) ; RDV actif qui chevauche pour le même praticien ou le même patient (`conflict`, avec les ressources en cause) ; règles de réservation (`rule_violation`, avec les règles enfreintes) ; aucune salle libre pour un type qui en exige (`no_room_available`) (praticien inactif)
    Given the clinician "A" is inactive
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "not_found"
    And nothing was written

  Scenario: Le placement s'arrête au premier échec, dans cet ordre : type inactif, utilisateur praticien inactif ou départements différents (`not_found`) ; RDV actif qui chevauche pour le même praticien ou le même patient (`conflict`, avec les ressources en cause) ; règles de réservation (`rule_violation`, avec les règles enfreintes) ; aucune salle libre pour un type qui en exige (`no_room_available`) (départements différents)
    Given the clinician "A" is in another department
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "not_found"
    And nothing was written

  Scenario: Le placement s'arrête au premier échec, dans cet ordre : type inactif, utilisateur praticien inactif ou départements différents (`not_found`) ; RDV actif qui chevauche pour le même praticien ou le même patient (`conflict`, avec les ressources en cause) ; règles de réservation (`rule_violation`, avec les règles enfreintes) ; aucune salle libre pour un type qui en exige (`no_room_available`) (RDV actif du praticien qui chevauche)
    Given "A" has an active appointment from "2026-11-23 09:15" to "2026-11-23 09:45"
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "conflict"
    And the refusal names the resources "clinician"
    And nothing was written

  Scenario: Le placement s'arrête au premier échec, dans cet ordre : type inactif, utilisateur praticien inactif ou départements différents (`not_found`) ; RDV actif qui chevauche pour le même praticien ou le même patient (`conflict`, avec les ressources en cause) ; règles de réservation (`rule_violation`, avec les règles enfreintes) ; aucune salle libre pour un type qui en exige (`no_room_available`) (RDV actif du patient qui chevauche)
    Given the patient has an active appointment with "B" from "2026-11-23 08:45" to "2026-11-23 09:15"
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "conflict"
    And the refusal names the resources "patient"
    And nothing was written

  Scenario: Le placement s'arrête au premier échec, dans cet ordre : type inactif, utilisateur praticien inactif ou départements différents (`not_found`) ; RDV actif qui chevauche pour le même praticien ou le même patient (`conflict`, avec les ressources en cause) ; règles de réservation (`rule_violation`, avec les règles enfreintes) ; aucune salle libre pour un type qui en exige (`no_room_available`) (règles enfreintes)
    Given the appointment type is not bookable online
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "type_not_bookable_online"
    And nothing was written

  Scenario: Le placement s'arrête au premier échec, dans cet ordre : type inactif, utilisateur praticien inactif ou départements différents (`not_found`) ; RDV actif qui chevauche pour le même praticien ou le même patient (`conflict`, avec les ressources en cause) ; règles de réservation (`rule_violation`, avec les règles enfreintes) ; aucune salle libre pour un type qui en exige (`no_room_available`) (aucune salle libre)
    Given the room "R1" is used by someone else from "2026-11-23 09:00" to "2026-11-23 09:30"
    And the room "R2" is used by someone else from "2026-11-23 08:45" to "2026-11-23 09:15"
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "no_room_available"
    And nothing was written

  Scenario: Le placement s'arrête au premier échec, dans cet ordre : type inactif, utilisateur praticien inactif ou départements différents (`not_found`) ; RDV actif qui chevauche pour le même praticien ou le même patient (`conflict`, avec les ressources en cause) ; règles de réservation (`rule_violation`, avec les règles enfreintes) ; aucune salle libre pour un type qui en exige (`no_room_available`) (premier échec seulement)
    Given the appointment type is inactive
    And "A" has an active appointment from "2026-11-23 09:15" to "2026-11-23 09:45"
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "not_found"

  Scenario: Les règles sont : début au moins 120 minutes après maintenant (`lead_time_too_short`), moins de 3 réservations en ligne ouvertes pour le patient, à venir, actives, de source `ONLINE` ou `ROUND_ROBIN` (`too_many_open_bookings`), type réservable en ligne (`type_not_bookable_online`), début égal à l'un des créneaux libres (`outside_availability`) (début trop proche)
    Given "A" and "B" are free at "2026-11-20 11:00"
    When the patient books "A" at "2026-11-20 11:00"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "lead_time_too_short"
    And nothing was written

  Scenario: Les règles sont : début au moins 120 minutes après maintenant (`lead_time_too_short`), moins de 3 réservations en ligne ouvertes pour le patient, à venir, actives, de source `ONLINE` ou `ROUND_ROBIN` (`too_many_open_bookings`), type réservable en ligne (`type_not_bookable_online`), début égal à l'un des créneaux libres (`outside_availability`) (3 réservations en ligne ouvertes)
    Given the patient has 3 open online bookings
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "too_many_open_bookings"
    And nothing was written

  Scenario: Les règles sont : début au moins 120 minutes après maintenant (`lead_time_too_short`), moins de 3 réservations en ligne ouvertes pour le patient, à venir, actives, de source `ONLINE` ou `ROUND_ROBIN` (`too_many_open_bookings`), type réservable en ligne (`type_not_bookable_online`), début égal à l'un des créneaux libres (`outside_availability`) (type non réservable en ligne)
    Given the appointment type is not bookable online
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "type_not_bookable_online"
    And nothing was written

  Scenario: Les règles sont : début au moins 120 minutes après maintenant (`lead_time_too_short`), moins de 3 réservations en ligne ouvertes pour le patient, à venir, actives, de source `ONLINE` ou `ROUND_ROBIN` (`too_many_open_bookings`), type réservable en ligne (`type_not_bookable_online`), début égal à l'un des créneaux libres (`outside_availability`) (début hors des créneaux libres)
    When the patient books "A" at "2026-11-23 09:15"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "outside_availability"
    And nothing was written

  Scenario: Les règles sont : début au moins 120 minutes après maintenant (`lead_time_too_short`), moins de 3 réservations en ligne ouvertes pour le patient, à venir, actives, de source `ONLINE` ou `ROUND_ROBIN` (`too_many_open_bookings`), type réservable en ligne (`type_not_bookable_online`), début égal à l'un des créneaux libres (`outside_availability`) (plusieurs règles, dans l'ordre)
    Given the appointment type is not bookable online
    When the patient books "A" at "2026-11-20 11:00"
    Then the booking is refused as "rule_violation"
    And the refusal names the rules "lead_time_too_short, type_not_bookable_online, outside_availability"
    And nothing was written

  Scenario: L'heure de fin n'est jamais acceptée de l'appelant
    When the patient books "A" at "2026-11-23 09:00"
    Then the appointment ends 30 minutes after it starts
    And the booking offers no way to name an end time

  Scenario: Règle §5.2 : le placement crée un RDV réservé dans la salle par défaut du praticien, audité, avec les créneaux du praticien recalculés et la confirmation envoyée
    When the patient books "A" at "2026-11-23 09:00"
    Then the appointment is "BOOKED" in room "R1"
    And the audit holds "booking.appointment_booked"
    And the slots of "A" were refreshed
    And a confirmation was queued

  Scenario: Règle §5.2 : sans salle par défaut libre, le placement prend la première salle libre du département dans l'ordre des codes
    Given the room "R1" is used by someone else from "2026-11-23 09:00" to "2026-11-23 09:30"
    When the patient books "A" at "2026-11-23 09:00"
    Then the appointment is "BOOKED" in room "R2"

  Scenario: Règle §5.2 : un type qui n'exige pas de salle n'en reçoit aucune
    Given the appointment type needs no room
    When the patient books "A" at "2026-11-23 09:00"
    Then the appointment is "BOOKED" in no room
