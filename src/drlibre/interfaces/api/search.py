from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from django.http import HttpRequest
from ninja import Router, Schema

from drlibre.bootstrap.container import container
from drlibre.search.application.ports.inbound import (
    FirstSlot,
    HospitalResult,
    NextSlots,
    ProviderResult,
    SearchCriteria,
    SpecialtyResult,
)

router = Router(tags=["search"])


def local_iso(instant: datetime, time_zone: str) -> str:
    """The instant in the hospital's zone, so the offset tells the local hour."""
    return instant.astimezone(ZoneInfo(time_zone)).isoformat()


class NextSlotsOut(Schema):
    type_id: UUID
    type_name: str
    duration_minutes: int
    starts: list[str]

    @staticmethod
    def of(slots: NextSlots, time_zone: str) -> "NextSlotsOut":
        return NextSlotsOut(
            type_id=slots.type_id.value,
            type_name=slots.type_name,
            duration_minutes=slots.duration_minutes,
            starts=[local_iso(s, time_zone) for s in slots.starts],
        )


class FirstSlotOut(Schema):
    start: str
    type_id: UUID
    type_name: str
    department_id: UUID

    @staticmethod
    def of(first: FirstSlot | None, time_zone: str | None) -> "FirstSlotOut | None":
        if first is None or time_zone is None:
            return None
        return FirstSlotOut(
            start=local_iso(first.start, time_zone),
            type_id=first.type_id.value,
            type_name=first.type_name,
            department_id=first.department_id.value,
        )


class ProviderOut(Schema):
    id: UUID
    full_name: str
    title: str
    specialty: str
    hospital_id: UUID
    hospital: str
    department: str
    city: str
    time_zone: str
    next_slots: NextSlotsOut | None
    distance_km: float | None

    @staticmethod
    def of(item: ProviderResult) -> "ProviderOut":
        return ProviderOut(
            id=item.id.value,
            full_name=item.full_name,
            title=item.title,
            specialty=item.specialty_name,
            hospital_id=item.hospital_id.value,
            hospital=item.hospital_name,
            department=item.department_name,
            city=item.city,
            time_zone=item.time_zone,
            next_slots=NextSlotsOut.of(item.next_slots, item.time_zone)
            if item.next_slots
            else None,
            distance_km=item.distance_km,
        )


class HospitalOut(Schema):
    id: UUID
    name: str
    street: str
    postal_code: str
    city: str
    time_zone: str
    specialties: list[str]
    providers: int
    providers_with_slots: int
    first_slot: FirstSlotOut | None
    distance_km: float | None

    @staticmethod
    def of(item: HospitalResult) -> "HospitalOut":
        return HospitalOut(
            id=item.id.value,
            name=item.name,
            street=item.street,
            postal_code=item.postal_code,
            city=item.city,
            time_zone=item.time_zone,
            specialties=list(item.specialties),
            providers=item.providers,
            providers_with_slots=item.providers_with_slots,
            first_slot=FirstSlotOut.of(item.first_slot, item.time_zone),
            distance_km=item.distance_km,
        )


class SpecialtyOut(Schema):
    id: UUID
    name: str
    providers: int
    hospitals: int
    time_zone: str | None
    first_slot: FirstSlotOut | None
    distance_km: float | None

    @staticmethod
    def of(item: SpecialtyResult) -> "SpecialtyOut":
        return SpecialtyOut(
            id=item.id.value,
            name=item.name,
            providers=item.providers,
            hospitals=item.hospitals,
            time_zone=item.time_zone,
            first_slot=FirstSlotOut.of(item.first_slot, item.time_zone),
            distance_km=item.distance_km,
        )


class PageOut(Schema):
    total: int
    page: int
    pages: int
    size: int


class ProvidersOut(PageOut):
    items: list[ProviderOut]


class HospitalsOut(PageOut):
    items: list[HospitalOut]


class SpecialtiesOut(PageOut):
    items: list[SpecialtyOut]


def criteria_of(request: HttpRequest) -> SearchCriteria:
    # Every value is optional and an unusable one falls back, so the query is read untyped.
    return SearchCriteria.parse(request.GET.dict())


@router.get("/search/providers", response=ProvidersOut)
def search_providers(request: HttpRequest) -> ProvidersOut:
    page = container().search_providers.execute(criteria_of(request))
    return ProvidersOut(
        total=page.total,
        page=page.number,
        pages=page.pages,
        size=page.size,
        items=[ProviderOut.of(i) for i in page.items],
    )


@router.get("/search/hospitals", response=HospitalsOut)
def search_hospitals(request: HttpRequest) -> HospitalsOut:
    page = container().search_hospitals.execute(criteria_of(request))
    return HospitalsOut(
        total=page.total,
        page=page.number,
        pages=page.pages,
        size=page.size,
        items=[HospitalOut.of(i) for i in page.items],
    )


@router.get("/search/specialties", response=SpecialtiesOut)
def search_specialties(request: HttpRequest) -> SpecialtiesOut:
    page = container().search_specialties.execute(criteria_of(request))
    return SpecialtiesOut(
        total=page.total,
        page=page.number,
        pages=page.pages,
        size=page.size,
        items=[SpecialtyOut.of(i) for i in page.items],
    )
