from datetime import date
from uuid import UUID

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from drlibre.bootstrap.container import container
from drlibre.interfaces.web.presenters.public import (
    hospital_page_view,
    provider_page_view,
    specialty_page_view,
)
from drlibre.search.application.ports.inbound import SearchCriteria
from drlibre.shared_kernel.ids import Id


def _day(raw: str | None) -> date | None:
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


def _id(raw: str | None) -> Id | None:
    try:
        return Id(UUID(raw)) if raw else None
    except ValueError:
        return None


@require_GET
def provider(request: HttpRequest, record_id: UUID) -> HttpResponse:
    page = container().view_provider_page.execute(
        provider_id=Id(record_id),
        type_id=_id(request.GET.get("type")),
        week=_day(request.GET.get("week")),
    )
    return render(request, "public/provider.html", {"view": provider_page_view(page)})


@require_GET
def hospital(request: HttpRequest, record_id: UUID) -> HttpResponse:
    page = container().view_hospital_page.execute(hospital_id=Id(record_id))
    return render(request, "public/hospital.html", {"view": hospital_page_view(page)})


@require_GET
def specialty(request: HttpRequest, record_id: UUID) -> HttpResponse:
    criteria = SearchCriteria.parse(request.GET.dict())
    page = container().view_specialty_page.execute(specialty_id=Id(record_id), criteria=criteria)
    return render(request, "public/specialty.html", {"view": specialty_page_view(page, criteria)})
