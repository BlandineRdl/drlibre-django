from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.presenters.forms import Choice, FieldSpec

ROLE_LABELS = {Role.ADMIN: "Admin", Role.CLINICIAN: "Praticien", Role.PATIENT: "Patient"}
ROLE_CHOICES = tuple(Choice(role.value, label) for role, label in ROLE_LABELS.items())

USER_FIELDS = (
    FieldSpec("full_name", "Nom complet", autocomplete="name"),
    FieldSpec("email", "Email", kind="email", help="Unique, enregistré en minuscules."),
    FieldSpec("role", "Rôle", kind="select"),
    FieldSpec("active", "Actif", kind="checkbox", required=False),
)
TEMPORARY_PASSWORD = FieldSpec(
    "temporary_password",
    "Mot de passe temporaire",
    kind="password",
    autocomplete="new-password",
    help="De 10 à 72 caractères ; la personne le changera à sa première connexion.",
)

PROFILE_FIELDS = (
    FieldSpec("department_id", "Département", kind="select"),
    FieldSpec("specialty_id", "Spécialité", kind="select"),
    FieldSpec("title", "Titre", help="Affiché publiquement, par exemple Dr Ana Bel."),
    FieldSpec("bio", "Bio", kind="textarea", required=False),
    FieldSpec(
        "default_room_id",
        "Salle par défaut",
        kind="select",
        required=False,
        help="Une salle active du département choisi.",
    ),
    FieldSpec("weight", "Poids round robin", kind="number", required=False, help="1 par défaut."),
)
CLINICIAN_FIELD = FieldSpec("user_id", "Praticien", kind="select")


def role_label(role: Role) -> str:
    return ROLE_LABELS[role]
