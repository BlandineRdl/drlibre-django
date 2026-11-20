from django.db import models
from django.db.models import Q

from drlibre.organisation.application.ports.inbound import (
    AppointmentType,
    ClinicianProfile,
    Department,
    Hospital,
    Option,
    ReferenceQueries,
    Room,
    Specialty,
)
from drlibre.organisation.infrastructure.django.models import (
    AppointmentTypeRecord,
    ClinicianProfileRecord,
    DepartmentRecord,
    HospitalRecord,
    RoomRecord,
    SpecialtyRecord,
)
from drlibre.organisation.infrastructure.mapping import from_row
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest


def _page[T](model: type[models.Model], entity: type[T], request: PageRequest) -> Page[T]:
    rows = model._default_manager.order_by("name", "code")
    if request.search:
        rows = rows.filter(Q(name__icontains=request.search) | Q(code__icontains=request.search))
    total = rows.count()
    window = rows[request.offset : request.offset + PAGE_SIZE]
    return Page(tuple(from_row(entity, row) for row in window), total, request.number)


def _one[T](model: type[models.Model], entity: type[T], record_id: Id) -> T | None:
    row = model._default_manager.filter(id=record_id.value).first()
    return from_row(entity, row) if row else None


def _label(name: str, code: str) -> str:
    return f"{name} ({code})"


class DjangoReferenceQueries(ReferenceQueries):
    def hospitals(self, request: PageRequest) -> Page[Hospital]:
        return _page(HospitalRecord, Hospital, request)

    def specialties(self, request: PageRequest) -> Page[Specialty]:
        return _page(SpecialtyRecord, Specialty, request)

    def departments(self, request: PageRequest) -> Page[Department]:
        return _page(DepartmentRecord, Department, request)

    def rooms(self, request: PageRequest) -> Page[Room]:
        return _page(RoomRecord, Room, request)

    def appointment_types(self, request: PageRequest) -> Page[AppointmentType]:
        return _page(AppointmentTypeRecord, AppointmentType, request)

    def hospital(self, record_id: Id) -> Hospital | None:
        return _one(HospitalRecord, Hospital, record_id)

    def specialty(self, record_id: Id) -> Specialty | None:
        return _one(SpecialtyRecord, Specialty, record_id)

    def department(self, record_id: Id) -> Department | None:
        return _one(DepartmentRecord, Department, record_id)

    def room(self, record_id: Id) -> Room | None:
        return _one(RoomRecord, Room, record_id)

    def appointment_type(self, record_id: Id) -> AppointmentType | None:
        return _one(AppointmentTypeRecord, AppointmentType, record_id)

    def hospital_options(self) -> tuple[Option, ...]:
        rows = HospitalRecord.objects.order_by("name").values_list("id", "name", "code")
        return tuple(Option(Id(pk), _label(name, code)) for pk, name, code in rows)

    def specialty_options(self) -> tuple[Option, ...]:
        rows = SpecialtyRecord.objects.order_by("name").values_list("id", "name", "code")
        return tuple(Option(Id(pk), _label(name, code)) for pk, name, code in rows)

    def department_options(self) -> tuple[Option, ...]:
        rows = DepartmentRecord.objects.order_by("name").values_list(
            "id", "name", "code", "hospital__name"
        )
        return tuple(
            Option(Id(pk), f"{_label(name, code)} · {hospital}")
            for pk, name, code, hospital in rows
        )

    def room_options(self) -> tuple[Option, ...]:
        rows = (
            RoomRecord.objects.filter(active=True)
            .order_by("name")
            .values_list("id", "name", "code", "department__name")
        )
        return tuple(
            Option(Id(pk), f"{_label(name, code)} · {department}")
            for pk, name, code, department in rows
        )

    def clinician_profiles(self, request: PageRequest) -> Page[ClinicianProfile]:
        rows = ClinicianProfileRecord.objects.order_by("title")
        if request.search:
            rows = rows.filter(title__icontains=request.search)
        window = rows[request.offset : request.offset + PAGE_SIZE]
        return Page(
            tuple(from_row(ClinicianProfile, r) for r in window), rows.count(), request.number
        )

    def clinician_profile(self, profile_id: Id) -> ClinicianProfile | None:
        return _one(ClinicianProfileRecord, ClinicianProfile, profile_id)

    def profiled_user_ids(self) -> frozenset[Id]:
        return frozenset(
            Id(pk) for pk in ClinicianProfileRecord.objects.values_list("user_id", flat=True)
        )
