from django.conf import settings
from django.http import HttpRequest

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import HOMES, identity_of
from drlibre.interfaces.web.presenters.shell import shell_view


def shell(request: HttpRequest) -> dict[str, object]:
    identity = identity_of(request)
    if identity is None:
        view = shell_view(request.path)
    else:
        unread = (
            container().count_unread.execute(recipient_id=identity.user_id)
            if identity.role is Role.PATIENT
            else 0
        )
        view = shell_view(
            request.path,
            role=identity.role,
            full_name=identity.full_name,
            has_password=identity.has_password,
            home_url=HOMES[identity.role],
            unread=unread,
        )
    return {"time_zone": settings.TIME_ZONE, "shell": view}
