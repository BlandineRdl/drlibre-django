from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.dashboard import dashboard_view
from drlibre.reporting.application.ports.inbound import Range


@require_GET
@require_role(Role.ADMIN)
def console_home(request: HttpRequest) -> HttpResponse:
    dashboard = container().view_dashboard.execute(
        actor_id=current_identity(request).user_id, period=Range.parse(request.GET.get("range"))
    )
    context = {"view": dashboard_view(dashboard), "section_nav": console_nav(request.path)}
    return render(request, "console/dashboard.html", context)
