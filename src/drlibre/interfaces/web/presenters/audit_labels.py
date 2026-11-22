ENTITY_LABELS = {
    "api_token": "Jeton d'API",
    "appointment": "Rendez-vous",
    "appointment_type": "Type de RDV",
    "availability_rule": "Plage hebdomadaire",
    "booking_hold": "Créneau tenu",
    "clinician_profile": "Profil praticien",
    "department": "Département",
    "hospital": "Hôpital",
    "notification": "Notification",
    "room": "Salle",
    "session": "Session",
    "specialty": "Spécialité",
    "time_off": "Absence",
    "user": "Utilisateur",
    "waitlist_entry": "Inscription en liste d'attente",
}
ACTION_LABELS = {
    "auth.login_failed": "Connexion refusée",
    "auth.login_locked": "Compte verrouillé",
    "auth.login_succeeded": "Connexion",
    "auth.logout": "Déconnexion",
    "booking.appointment_booked": "RDV réservé",
    "booking.appointment_cancelled": "RDV annulé",
    "booking.appointment_notes_written": "Notes cliniques enregistrées",
    "booking.appointment_rescheduled": "RDV déplacé",
    "booking.appointment_status_changed": "Statut modifié",
    "booking.appointments_exported": "RDV exportés",
    "booking.code_failed": "Code erroné",
    "booking.hold_created": "Créneau tenu",
    "booking.hold_expired": "Créneau tenu expiré",
    "booking.hold_released": "Créneau tenu libéré",
    "booking.reminders_sent": "Rappels envoyés",
    "booking.waitlist_accepted": "Offre de liste d'attente acceptée",
    "booking.waitlist_expired": "Inscription en liste d'attente expirée",
    "booking.waitlist_joined": "Inscription en liste d'attente",
    "booking.waitlist_offer_lapsed": "Offre de liste d'attente caduque",
    "booking.waitlist_offered": "Créneau proposé en liste d'attente",
    "identity.api_token_issued": "Jeton d'API émis",
    "identity.api_tokens_revoked": "Jetons d'API révoqués",
    "identity.link_refused": "Lien de connexion refusé",
    "identity.link_requested": "Lien de connexion demandé",
    "identity.link_used": "Connexion par lien",
    "identity.patient_created": "Patient créé",
    "notification.read": "Notification lue",
    "user.password_changed": "Mot de passe changé",
    "user.profile_updated": "Profil modifié",
}
_VERBS = {"created": "créé", "updated": "modifié", "deleted": "supprimé"}


def entity_label(entity_type: str) -> str:
    return ENTITY_LABELS.get(entity_type, entity_type)


def action_label(action: str) -> str:
    """The French wording of an audit action; a reference write reads « Salle : créé »."""
    if action in ACTION_LABELS:
        return ACTION_LABELS[action]
    entity, _, verb = action.partition(".")
    if entity in ENTITY_LABELS and verb in _VERBS:
        return f"{ENTITY_LABELS[entity]} : {_VERBS[verb]}"
    return action
