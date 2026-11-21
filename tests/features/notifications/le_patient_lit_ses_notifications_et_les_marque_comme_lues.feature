Feature: Le patient lit ses notifications et les marque comme lues
  En tant que patient connecté, avec ou sans mot de passe
  Je veux lire mes notifications et les marquer comme lues
  Afin que je sache ce qui a changé sur mes RDV

  Background:
    Given a signed-in patient
    And a clinician free at "2026-11-25 13:30" seen in "Europe/Paris"

  Scenario: Une réservation crée la notification « RDV réservé » (type « Changement de planning ») dans la même transaction que le RDV ; elle n'envoie que l'email de confirmation de l'Epic 3, aucun second email
    When the patient books that clinician at "2026-11-25 13:30"
    Then the patient has one notification "RDV réservé" of kind "SCHEDULE_CHANGED" for that appointment
    And the only email queued is the confirmation

  Scenario: Une réservation crée la notification « RDV réservé » (type « Changement de planning ») dans la même transaction que le RDV ; elle n'envoie que l'email de confirmation de l'Epic 3, aucun second email (réservation annulée par une erreur)
    Given the audit log is unavailable
    When the patient books that clinician at "2026-11-25 13:30"
    Then no appointment, notification or email remains

  Scenario: Une réservation crée la notification « RDV réservé » (type « Changement de planning ») dans la même transaction que le RDV ; elle n'envoie que l'email de confirmation de l'Epic 3, aucun second email (réservation refusée)
    When the patient books that clinician at "2026-11-25 15:00"
    Then the booking is refused as "rule_violation"
    And no appointment, notification or email remains

  Scenario: Le texte d'une notification ne porte que l'heure du RDV : ni nom, ni motif, ni email
    When a visitor books that clinician at "2026-11-25 13:30" with the reason "Douleur au genou"
    Then the notification reads "Votre RDV du 25/11/2026 à 14:30 (Europe/Paris) est réservé."
    And the notification names neither the provider, the visitor, the reason nor the email

  Scenario: La liste montre les notifications du patient, des plus récentes aux plus anciennes, et seulement les siennes
    Given the patient has notifications created at "2026-11-18 09:00, 2026-11-19 09:00, 2026-11-17 09:00"
    And another patient has a notification created at "2026-11-19 12:00"
    When the patient lists their notifications
    Then they see the notifications created at "2026-11-19 09:00, 2026-11-18 09:00, 2026-11-17 09:00"

  Scenario: « Marquer comme lu » fait passer la notification en lue ; l'écriture laisse une entrée d'audit sans donnée personnelle
    Given the patient has notifications created at "2026-11-18 09:00, 2026-11-19 09:00"
    When the patient marks the notification created at "2026-11-18 09:00" read
    Then that notification is read at "2026-11-20 10:00"
    And the patient has 1 unread notification
    And the audit holds "notification.read" naming only the notification and its kind

  Scenario: « Marquer comme lu » fait passer la notification en lue ; l'écriture laisse une entrée d'audit sans donnée personnelle (déjà lue)
    Given the patient has notifications created at "2026-11-18 09:00"
    And the patient marked the notification created at "2026-11-18 09:00" read
    And an hour passes
    When the patient marks the notification created at "2026-11-18 09:00" read
    Then that notification is read at "2026-11-20 10:00"
    And the audit holds "notification.read" naming only the notification and its kind

  Scenario: « Marquer comme lu » fait passer la notification en lue ; l'écriture laisse une entrée d'audit sans donnée personnelle (notification d'un autre patient)
    Given another patient has a notification created at "2026-11-19 12:00"
    When the patient marks that other notification read
    Then the marking is refused as "forbidden"
    And the other notification is still unread and nothing was audited

  Scenario: « Marquer comme lu » fait passer la notification en lue ; l'écriture laisse une entrée d'audit sans donnée personnelle (notification inconnue)
    When the patient marks an unknown notification read
    Then the marking is refused as "not_found"
