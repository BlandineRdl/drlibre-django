from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from drlibre.audit.application.ports.inbound import JournalQuery
from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import current_identity, require_role
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.console_audit import AUDIT_URL, actor_email, audit_page
from drlibre.shared_kernel.pagination import PageRequest


@require_GET
@require_role(Role.ADMIN)
def journal(request: HttpRequest) -> HttpResponse:
    query = request.GET
    email = actor_email(query.get("actor"))
    journal = container().view_audit_journal.execute(
        actor_id=current_identity(request).user_id,
        query=JournalQuery(
            email=email or None,
            entity_type=query.get("entity_type"),
            start=query.get("from"),
            end=query.get("to"),
            request=PageRequest.from_query(page=query.get("page"), search=None),
        ),
    )
    view = audit_page(
        journal.page,
        journal.audit_filter,
        email=email,
        entity_types=journal.entity_types,
        emails=journal.emails,
        time_zone=journal.time_zone,
    )
    context = {"view": view, "section_nav": console_nav(AUDIT_URL)}
    return render(request, "console/audit.html", context)
