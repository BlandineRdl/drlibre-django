from datetime import date
from uuid import UUID

from django.http import HttpRequest
from ninja import Router, Schema

from drlibre.bootstrap.container import container
from drlibre.interfaces.api.search import (
    PageOut,
    ProviderOut,
    criteria_of,
    local_iso,
)
from drlibre.shared_kernel.ids import Id

router = Router(tags=["public pages"])


class BookableTypeOut(Schema):
    id: UUID
    name: str
    duration_minutes: int


class ProviderPageOut(Schema):
    id: UUID
    full_name: str
    title: str
    specialty: str
    bio: str
    hospital_id: UUID
    hospital: str
    department_id: UUID
    department: str
    city: str
    time_zone: str
    types: list[BookableTypeOut]
    type_id: UUID
    week_start: date
    previous_week: date | None
    next_week: date | None
    starts: list[str]


class FirstByTypeOut(Schema):
    type_id: UUID
    type_name: str
    duration_minutes: int
    department_id: UUID
    department: str
    start: str | None


class HospitalPageOut(Schema):
    id: UUID
    name: str
    street: str
    postal_code: str
    city: str
    country: str
    phone: str
    description: str
    time_zone: str
    departments: list[str]
    specialties: list[str]
    first_by_type: list[FirstByTypeOut]
    providers: list[ProviderOut]


class SpecialtyPageOut(PageOut):
    id: UUID
    name: str
    providers: list[ProviderOut]


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


@router.get("/providers/{provider_id}", response=ProviderPageOut)
def provider_page(
    request: HttpRequest, provider_id: UUID, type: str | None = None, week: str | None = None
) -> ProviderPageOut:
    page = container().view_provider_page.execute(
        provider_id=Id(provider_id), type_id=_id(type), week=_day(week)
    )
    d = page.detail
    return ProviderPageOut(
        id=d.id.value,
        full_name=d.full_name,
        title=d.title,
        specialty=d.specialty_name,
        bio=d.bio,
        hospital_id=d.hospital_id.value,
        hospital=d.hospital_name,
        department_id=d.department_id.value,
        department=d.department_name,
        city=d.city,
        time_zone=d.time_zone,
        types=[
            BookableTypeOut(id=t.id.value, name=t.name, duration_minutes=t.duration_minutes)
            for t in d.types
        ],
        type_id=page.type_id.value,
        week_start=page.monday,
        previous_week=page.previous_monday,
        next_week=page.next_monday,
        starts=[local_iso(s, d.time_zone) for s in page.starts],
    )


@router.get("/hospitals/{hospital_id}", response=HospitalPageOut)
def hospital_page(request: HttpRequest, hospital_id: UUID) -> HospitalPageOut:
    page = container().view_hospital_page.execute(hospital_id=Id(hospital_id))
    d = page.detail
    return HospitalPageOut(
        id=d.id.value,
        name=d.name,
        street=d.street,
        postal_code=d.postal_code,
        city=d.city,
        country=d.country,
        phone=d.phone,
        description=d.description,
        time_zone=d.time_zone,
        departments=list(d.departments),
        specialties=list(d.specialties),
        first_by_type=[
            FirstByTypeOut(
                type_id=f.type_id.value,
                type_name=f.type_name,
                duration_minutes=f.duration_minutes,
                department_id=f.department_id.value,
                department=f.department_name,
                start=local_iso(f.start, d.time_zone) if f.start else None,
            )
            for f in page.first_by_type
        ],
        providers=[ProviderOut.of(p) for p in page.providers],
    )


@router.get("/specialties/{specialty_id}", response=SpecialtyPageOut)
def specialty_page(request: HttpRequest, specialty_id: UUID) -> SpecialtyPageOut:
    page = container().view_specialty_page.execute(
        specialty_id=Id(specialty_id), criteria=criteria_of(request)
    )
    found = page.providers
    return SpecialtyPageOut(
        id=page.detail.id.value,
        name=page.detail.name,
        total=found.total,
        page=found.number,
        pages=found.pages,
        size=found.size,
        providers=[ProviderOut.of(p) for p in found.items],
    )
