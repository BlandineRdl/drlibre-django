from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.labels import ROLE_LABELS


def role_label(role: Role) -> str:
    return ROLE_LABELS[role]
