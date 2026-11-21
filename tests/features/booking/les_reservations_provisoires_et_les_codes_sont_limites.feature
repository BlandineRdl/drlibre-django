Feature: Les réservations provisoires et les codes sont limités
  En tant que visiteur
  Je veux que le créneau que je tiens ne soit proposé à personne d'autre le temps de valider mon code
  Afin que personne ne me le prenne, sans que quiconque puisse accaparer des créneaux

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And "A" is free every 30 minutes from "2026-11-23 09:00" for 25 slots

  Scenario: Dès sa création, un créneau tenu disparaît de la recherche, des pages publiques et de `GET /slots`, et toute réservation qui le chevauche échoue en `conflict` (créneau libéré aux autres)
    When the visitor asks to hold "A" at "2026-11-23 09:00"
    Then the slot of "A" at "2026-11-23 09:00" is no longer offered

  Scenario: Dès sa création, un créneau tenu disparaît de la recherche, des pages publiques et de `GET /slots`, et toute réservation qui le chevauche échoue en `conflict` (second visiteur)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When "autre@example.org" asks to hold "A" at "2026-11-23 09:00"
    Then the booking is refused as "conflict"
    And the refusal names the resources "clinician"

  Scenario: Dès sa création, un créneau tenu disparaît de la recherche, des pages publiques et de `GET /slots`, et toute réservation qui le chevauche échoue en `conflict` (patient connecté)
    Given a signed-in patient
    And the visitor asks to hold "A" at "2026-11-23 09:00"
    When the patient books "A" at "2026-11-23 09:00"
    Then the booking is refused as "conflict"
    And the refusal names the resources "clinician"

  Scenario: Un email n'a jamais plus d'une réservation provisoire ouverte à la fois
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor asks to hold "A" at "2026-11-23 09:30"
    Then the slot of "A" at "2026-11-23 09:00" is offered again
    And the slot of "A" at "2026-11-23 09:30" is no longer offered
    And only the second hold and its code remain

  Scenario: Le créneau redevient libre dès l'heure d'expiration, même avant le passage du job d'expiration ; ce job tourne chaque minute et audite chaque expiration avec le domaine de l'email (avant le job)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When 10 minutes pass
    Then the slot of "A" at "2026-11-23 09:00" is offered again
    And the hold is still there

  Scenario: Le créneau redevient libre dès l'heure d'expiration, même avant le passage du job d'expiration ; ce job tourne chaque minute et audite chaque expiration avec le domaine de l'email (audit par le job)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    And 10 minutes pass
    When the expiry job runs
    Then the hold is gone
    And the audit entry "booking.hold_expired" has no actor and only the email domain

  Scenario: Règle §7.1 : une réservation provisoire ouverte est lisible comme période tenue, une expirée ne l'est plus
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    Then 1 period of "A" is held on "2026-11-23"
    When 10 minutes pass
    Then 0 period of "A" is held on "2026-11-23"

  Scenario: Si le code n'est jamais saisi, aucun RDV ni compte n'est créé
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    And 10 minutes pass
    When the expiry job runs
    Then no appointment and no account exist

  Scenario: Un code vaut 10 minutes et 5 essais ; au-delà, il n'est plus accepté ; chaque échec est audité avec le domaine de l'email (10 minutes)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    And 10 minutes pass
    When the visitor enters the code "123456"
    Then the booking is refused as "not_found"

  Scenario: Un code vaut 10 minutes et 5 essais ; au-delà, il n'est plus accepté ; chaque échec est audité avec le domaine de l'email (5 essais)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters a wrong code 5 times
    And the visitor enters the code "123456"
    Then the booking is refused as "invalid_input"
    And the refusal names the field "code"
    And no appointment and no account exist

  Scenario: Un code vaut 10 minutes et 5 essais ; au-delà, il n'est plus accepté ; chaque échec est audité avec le domaine de l'email (échecs audités)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters a wrong code 3 times
    Then the audit holds 3 "booking.code_failed" entries
    And the audit entry "booking.code_failed" has no actor and only the email domain

  Scenario: Un code vaut 10 minutes et 5 essais ; au-delà, il n'est plus accepté ; chaque échec est audité avec le domaine de l'email (code redemandé après 10 minutes)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    And 9 minutes pass
    And the sent code is "654321"
    When the visitor asks for a new code
    And 2 minutes pass
    And the visitor enters the code "654321"
    Then the booking is refused as "not_found"

  Scenario: `POST /booking/holds/{id}/resend` envoie un nouveau code, 3 fois par heure et par email au plus (nouveau code)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    And the sent code is "654321"
    When the visitor asks for a new code
    And the visitor enters the code "123456"
    Then the booking is refused as "invalid_input"

  Scenario: `POST /booking/holds/{id}/resend` envoie un nouveau code, 3 fois par heure et par email au plus (nouveau code accepté sans prolonger la réservation)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    And the sent code is "654321"
    And 5 minutes pass
    When the visitor asks for a new code
    And the visitor enters the code "654321"
    Then the appointment is "BOOKED" for "ONLINE"
    And 2 code emails were sent in all

  Scenario: `POST /booking/holds/{id}/resend` envoie un nouveau code, 3 fois par heure et par email au plus (limite)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor asks for a new code 4 times
    Then the first 3 requests succeeded and the next was refused as "too_many_requests"

  Scenario: Règle §7.5 : au plus 3 réservations provisoires par heure et par email
    When the visitor asks to hold "A" at "2026-11-23 09:00" 4 times
    Then the first 3 requests succeeded and the next was refused as "too_many_requests"

  Scenario: Une même adresse réseau crée au plus 20 réservations provisoires et demande au plus 20 codes par heure (réservations provisoires)
    When 21 visitors on network "10.0.0.9" ask to hold "A" from "2026-11-23 09:00" on
    Then the first 20 requests succeeded and the next was refused as "too_many_requests"

  Scenario: Une même adresse réseau crée au plus 20 réservations provisoires et demande au plus 20 codes par heure (codes)
    Given 21 holds were made from separate networks from "2026-11-23 09:00" on "A"
    When a new code is asked for each of them from network "10.0.0.9"
    Then the first 20 requests succeeded and the next was refused as "too_many_requests"
