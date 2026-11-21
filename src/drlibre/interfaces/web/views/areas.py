from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import require_role
from drlibre.interfaces.web.presenters.console import console_nav


@require_GET
@require_role(Role.ADMIN)
def console_home(request: HttpRequest) -> HttpResponse:
    context = {
        "title": "Console d'administration",
        "intro": "Gérez le référentiel des hôpitaux et les comptes depuis le menu.",
        "section_nav": console_nav(request.path),
    }
    return render(request, "areas/home.html", context)
