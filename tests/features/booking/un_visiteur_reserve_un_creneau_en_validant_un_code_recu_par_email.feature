Feature: Un visiteur réserve un créneau en validant un code reçu par email
  En tant que visiteur
  Je veux réserver le créneau d'un praticien nommé en validant un code reçu par email, sans mot de passe
  Afin que j'obtienne un RDV et un compte patient en une seule démarche

  Background:
    Given a department with an online appointment type of 30 minutes needing a room
    And rooms "R1, R2" in that department
    And an active clinician "A" with default room "R1" in that department
    And "A" is free every 30 minutes from "2026-11-23 09:00" for 2 slots

  Scenario: Le visiteur saisit nom complet, date de naissance, email, téléphone facultatif, motif facultatif, et accepte les conditions et la notice de confidentialité
    Given the visitor leaves the phone and the reason empty
    When the visitor asks to hold "A" at "2026-11-23 09:00"
    Then the hold is on "A"

  Scenario: Le visiteur saisit nom complet, date de naissance, email, téléphone facultatif, motif facultatif, et accepte les conditions et la notice de confidentialité (conditions refusées)
    Given the visitor does not accept the terms
    When the visitor asks to hold "A" at "2026-11-23 09:00"
    Then the booking is refused as "invalid_input"
    And the refusal names the field "accepted_terms"
    And no hold was created

  Scenario: Le visiteur saisit nom complet, date de naissance, email, téléphone facultatif, motif facultatif, et accepte les conditions et la notice de confidentialité (informations invalides)
    Given the visitor types email "pas-un-email"
    And the visitor types birth_date "2999-01-01"
    When the visitor asks to hold "A" at "2026-11-23 09:00"
    Then the booking is refused as "invalid_input"
    And the refusal names the field "email"
    And the refusal names the field "birth_date"
    And no hold was created

  Scenario: L'envoi de ces informations crée une réservation provisoire de 10 minutes sur le créneau et envoie par email un code à 6 chiffres
    When the visitor asks to hold "A" at "2026-11-23 09:00"
    Then the hold expires at "2026-11-20 10:10"
    And the slot of "A" at "2026-11-23 09:00" is no longer offered
    And a 6 digit code was emailed to "lea@example.org"
    And the code email carries no link

  Scenario: Avec le bon code, le RDV est créé en `BOOKED`, source `ONLINE`, fin égale au début plus la durée du type, et la réservation provisoire disparaît
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the appointment is "BOOKED" for "ONLINE"
    And the appointment ends 30 minutes after it starts
    And the hold is gone

  Scenario: Si le type exige une salle, le RDV reçoit la salle par défaut du praticien si elle est libre, sinon la première salle active libre du département par ordre de code ; un type sans salle n'en reçoit pas (salle par défaut)
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the appointment is "BOOKED" in room "R1"

  Scenario: Si le type exige une salle, le RDV reçoit la salle par défaut du praticien si elle est libre, sinon la première salle active libre du département par ordre de code ; un type sans salle n'en reçoit pas (salle par défaut occupée)
    Given the room "R1" is used by someone else from "2026-11-23 09:00" to "2026-11-23 09:30"
    And the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the appointment is "BOOKED" in room "R2"

  Scenario: Si le type exige une salle, le RDV reçoit la salle par défaut du praticien si elle est libre, sinon la première salle active libre du département par ordre de code ; un type sans salle n'en reçoit pas (type sans salle)
    Given the appointment type needs no room
    And the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the appointment is "BOOKED" in no room

  Scenario: Un email inconnu crée un patient sans mot de passe, avec le nom, la date de naissance et le téléphone saisis, et l'email marqué vérifié
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then a patient without password was created from the typed details with a verified email

  Scenario: Le bon code ouvre une session de 24 h, jamais prolongée
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then a session of 24 hours that is never extended was opened for the patient

  Scenario: La réservation envoie un seul email, la confirmation : heure, hôpital et praticien, sans motif ; comme l'email du code, il ne contient aucun lien qui connecte, seulement un lien vers la page de connexion
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then exactly one confirmation email was sent
    And the confirmation names the time, hospital and provider and links to the sign-in page only
    And the code email carries no link

  Scenario: Sont audités avec le domaine de l'email seulement : réservation provisoire créée, compte patient créé, RDV pris ; l'acteur est vide avant la vérification, puis c'est le patient
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    When the visitor enters the code "123456"
    Then the audit entry "booking.hold_created" has no actor and only the email domain
    And the audit entry "identity.patient_created" has the patient as actor and only the email domain
    And the audit entry "booking.appointment_booked" has the patient as actor and only the email domain
    And no audit entry holds personal data

  Scenario: Règle §7.1 : avec le bon code mais un créneau pris entre-temps, le compte et la session restent, et l'échec est renvoyé sans réservation
    Given the visitor asks to hold "A" at "2026-11-23 09:00"
    And "A" has an active appointment from "2026-11-23 09:00" to "2026-11-23 09:30"
    When the visitor enters the code "123456"
    Then the booking failed as "conflict" while the patient session stays open
