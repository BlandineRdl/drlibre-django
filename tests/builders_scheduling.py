from datetime import date, datetime, time

from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.organisation.domain.department import Department
from drlibre.organisation.infrastructure.repositories import (
    DjangoClinicianProfiles,
    DjangoDepartments,
    DjangoHospitals,
    DjangoSpecialties,
)
from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.scheduling.domain.slot import Period
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build


def rule(
    clinician_id: Id,
    *,
    weekday: int,
    start: time = time(9),
    end: time = time(12),
    step_minutes: int = 15,
    valid_from: date = date(2026, 1, 1),
    valid_to: date | None = None,
    room_id: Id | None = None,
) -> AvailabilityRule:
    return AvailabilityRule(
        id=Id(),
        clinician_id=clinician_id,
        weekday=weekday,
        start=start,
        end=end,
        step_minutes=step_minutes,
        room_id=room_id,
        valid_from=valid_from,
        valid_to=valid_to,
    )


def time_off(clinician_id: Id, start: datetime, end: datetime) -> TimeOff:
    return TimeOff(id=Id(), clinician_id=clinician_id, start=start, end=end, reason="Congés")


def appointment(
    clinician_id: Id, start: datetime, end: datetime, *, status: str = "BOOKED"
) -> tuple[Id, Period, str]:
    return clinician_id, Period(start, end), status


def stored_department() -> Department:
    """A hospital and its department saved through the real organisation repositories."""
    hospital = build.hospital()
    DjangoHospitals().save(hospital)
    department = build.department(hospital.id)
    DjangoDepartments().save(department)
    return department


def stored_profile(department: Department, *, user_id: Id | None = None) -> ClinicianProfile:
    """A clinician profile saved through the real repository, for its foreign keys."""
    specialty = build.specialty()
    DjangoSpecialties().save(specialty)
    fields = {
        "department_id": str(department.id),
        "specialty_id": str(specialty.id),
        "title": "Dr X",
    }
    profile = ClinicianProfile.attach(fields, user_id=user_id or Id(), at=build.AT)
    DjangoClinicianProfiles().save(profile)
    return profile
