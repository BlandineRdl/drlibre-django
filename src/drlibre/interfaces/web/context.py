from django.conf import settings
from django.http import HttpRequest

from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import HOMES, identity_of


def shell(request: HttpRequest) -> dict[str, object]:
    identity = identity_of(request)
    return {
        "time_zone": settings.TIME_ZONE,
        "shell": {
            "signed_in": identity is not None,
            "home_url": HOMES[identity.role] if identity else "",
            "can_change_password": identity is not None and identity.has_password,
            "is_clinician": identity is not None and identity.role is Role.CLINICIAN,
        },
    }
