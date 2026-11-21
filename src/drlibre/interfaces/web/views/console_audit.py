from django.conf import settings
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from drlibre.audit.application.ports.inbound import AuditFilter, AuditRow
from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.auth import require_role
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.interfaces.web.presenters.console_audit import AUDIT_URL, actor_email, audit_page
from drlibre.shared_kernel.pagination import Page, PageRequest


@require_GET
@require_role(Role.ADMIN)
def journal(request: HttpRequest) -> HttpResponse:
    query, c, zone = request.GET, container(), settings.TIME_ZONE
    types = c.audit_queries.entity_types()
    email = actor_email(query.get("actor"))
    actor = c.user_queries.user_by_email(email) if email else None
    audit_filter = AuditFilter.from_query(
        actor_id=actor.id if actor else None,
        entity_type=query.get("entity_type"),
        start=query.get("from"),
        end=query.get("to"),
        time_zone=zone,
        entity_types=types,
    )
    page_request = PageRequest.from_query(page=query.get("page"), search=None)
    # An email of no user matches no entry.
    page: Page[AuditRow] = (
        Page((), 0, 1)
        if email and actor is None
        else c.audit_queries.page(audit_filter, page_request)
    )
    actors = {r.actor_id for r in page.items if r.actor_id is not None}
    emails = {i: u.email.value for i in actors if (u := c.user_queries.user(i)) is not None}
    view = audit_page(
        page, audit_filter, email=email, entity_types=types, emails=emails, time_zone=zone
    )
    context = {"view": view, "section_nav": console_nav(AUDIT_URL)}
    return render(request, "console/audit.html", context)
