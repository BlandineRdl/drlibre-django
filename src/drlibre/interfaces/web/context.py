from django.conf import settings
from django.http import HttpRequest

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import HOMES, identity_of
from drlibre.interfaces.web.presenters.portal import notifications_label, portal_nav
from drlibre.interfaces.web.presenters.workspace import workspace_nav

ROLE_LABELS = {Role.ADMIN: "Administration", Role.CLINICIAN: "Praticien", Role.PATIENT: "Patient"}


def shell(request: HttpRequest) -> dict[str, object]:
    identity = identity_of(request)
    is_patient = identity is not None and identity.role is Role.PATIENT
    is_clinician = identity is not None and identity.role is Role.CLINICIAN
    unread = (
        container().count_unread.execute(recipient_id=identity.user_id)
        if identity is not None and is_patient
        else 0
    )
    home_url = HOMES[identity.role] if identity else ""
    label = notifications_label(unread)
    return {
        "time_zone": settings.TIME_ZONE,
        "shell": {
            "signed_in": identity is not None,
            "home_url": home_url,
            "home_current": bool(home_url) and request.path.startswith(home_url),
            "role_label": ROLE_LABELS[identity.role] if identity else "",
            "can_change_password": identity is not None and identity.has_password,
            "is_clinician": is_clinician,
            "workspace_nav": workspace_nav(request.path) if is_clinician else (),
            "is_patient": is_patient,
            "notifications_label": label,
            "patient_nav": portal_nav(request.path, home_url, label) if is_patient else (),
        },
    }
