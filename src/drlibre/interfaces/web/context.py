from django.conf import settings
from django.http import HttpRequest

from drlibre.interfaces.web.auth import identity_of


def shell(request: HttpRequest) -> dict[str, object]:
    identity = identity_of(request)
    return {
        "time_zone": settings.TIME_ZONE,
        "shell": {
            "signed_in": identity is not None,
            "can_change_password": identity is not None and identity.has_password,
        },
    }
