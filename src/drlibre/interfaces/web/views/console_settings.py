from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.console_settings import SETTINGS_URL, settings_view


@require_GET
@require_role(Role.ADMIN)
def overview(request: HttpRequest) -> HttpResponse:
    view = settings_view(done=request.GET.get("done", ""), count=request.GET.get("count", ""))
    context = {"view": view, "section_nav": console_nav(SETTINGS_URL)}
    return render(request, "console/settings.html", context)


@require_POST
@require_role(Role.ADMIN)
def run_reminders(request: HttpRequest) -> HttpResponse:
    count = container().run_reminders.execute(actor_id=current_identity(request).user_id)
    return redirect(f"{SETTINGS_URL}?done=reminders&count={count}")
