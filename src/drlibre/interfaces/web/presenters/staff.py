from drlibre.identity.application.ports.inbound import Role

ROLE_LABELS = {Role.ADMIN: "Admin", Role.CLINICIAN: "Praticien", Role.PATIENT: "Patient"}


def role_label(role: Role) -> str:
    return ROLE_LABELS[role]
