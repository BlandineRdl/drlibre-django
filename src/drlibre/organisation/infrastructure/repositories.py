from django.db import models
from django.db.models import ProtectedError

from drlibre.organisation.application.ports.outbound import (
    AppointmentTypes,
    ClinicianProfiles,
    Departments,
    Hospitals,
    Rooms,
    Specialties,
)
from drlibre.organisation.domain.appointment_type import AppointmentType
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.domain.department import Department
from drlibre.organisation.domain.hospital import Hospital
from drlibre.organisation.domain.room import Room
from drlibre.organisation.domain.specialty import Specialty
from drlibre.organisation.infrastructure.django.models import (
    AppointmentTypeRecord,
    ClinicianProfileRecord,
    DepartmentRecord,
    HospitalRecord,
    RoomRecord,
    SpecialtyRecord,
)
from drlibre.organisation.infrastructure.mapping import from_row, to_columns
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


class DjangoRecords[T]:
    def __init__(self, model: type[models.Model], entity: type[T]) -> None:
        self._model = model
        self._entity = entity

    def get(self, record_id: Id) -> T | None:
        row = self._model._default_manager.filter(id=record_id.value).first()
        return from_row(self._entity, row) if row else None

    def save(self, record: T) -> None:
        columns = to_columns(record)
        self._model._default_manager.update_or_create(id=columns.pop("id"), defaults=columns)

    def delete(self, record_id: Id) -> None:
        try:
            self._model._default_manager.filter(id=record_id.value).delete()
        except ProtectedError as error:
            # A child inserted concurrently after the dependents check.
            raise DomainError(
                ErrorCode.HAS_DEPENDENTS, "Cet élément est encore utilisé.", {"dependents": []}
            ) from error

    def code_taken(self, code: str, *, except_id: Id) -> bool:
        rows = self._model._default_manager.filter(code=code).exclude(id=except_id.value)
        return rows.exists()

    def _children(self, **lookup: object) -> tuple[T, ...]:
        rows = self._model._default_manager.filter(**lookup).order_by("name", "code")
        return tuple(from_row(self._entity, row) for row in rows)


class DjangoHospitals(DjangoRecords[Hospital], Hospitals):
    def __init__(self) -> None:
        super().__init__(HospitalRecord, Hospital)


class DjangoSpecialties(DjangoRecords[Specialty], Specialties):
    def __init__(self) -> None:
        super().__init__(SpecialtyRecord, Specialty)


class DjangoDepartments(DjangoRecords[Department], Departments):
    def __init__(self) -> None:
        super().__init__(DepartmentRecord, Department)

    def for_hospital(self, hospital_id: Id) -> tuple[Department, ...]:
        return self._children(hospital_id=hospital_id.value)


class DjangoRooms(DjangoRecords[Room], Rooms):
    def __init__(self) -> None:
        super().__init__(RoomRecord, Room)

    def for_department(self, department_id: Id) -> tuple[Room, ...]:
        return self._children(department_id=department_id.value)


class DjangoAppointmentTypes(DjangoRecords[AppointmentType], AppointmentTypes):
    def __init__(self) -> None:
        super().__init__(AppointmentTypeRecord, AppointmentType)

    def for_department(self, department_id: Id) -> tuple[AppointmentType, ...]:
        return self._children(department_id=department_id.value)


class DjangoClinicianProfiles(ClinicianProfiles):
    def get(self, profile_id: Id) -> ClinicianProfile | None:
        row = ClinicianProfileRecord.objects.filter(id=profile_id.value).first()
        return from_row(ClinicianProfile, row) if row else None

    def for_user(self, user_id: Id) -> ClinicianProfile | None:
        row = ClinicianProfileRecord.objects.filter(user_id=user_id.value).first()
        return from_row(ClinicianProfile, row) if row else None

    def save(self, profile: ClinicianProfile) -> None:
        columns = to_columns(profile)
        ClinicianProfileRecord.objects.update_or_create(id=columns.pop("id"), defaults=columns)

    def delete(self, profile_id: Id) -> None:
        ClinicianProfileRecord.objects.filter(id=profile_id.value).delete()

    def matching(
        self,
        *,
        department_id: Id | None = None,
        specialty_id: Id | None = None,
        default_room_id: Id | None = None,
    ) -> tuple[ClinicianProfile, ...]:
        criteria = {
            "department_id": department_id,
            "specialty_id": specialty_id,
            "default_room_id": default_room_id,
        }
        lookup = {name: value.value for name, value in criteria.items() if value is not None}
        rows = ClinicianProfileRecord.objects.filter(**lookup).order_by("title")
        return tuple(from_row(ClinicianProfile, row) for row in rows)
