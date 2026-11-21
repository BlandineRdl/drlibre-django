import dataclasses
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.booking.domain.appointment import AppointmentStatus, Source
from drlibre.booking.infrastructure.django.models import WaitlistEntryRecord
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.organisation.domain.department import Department
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoDepartments,
    DjangoHospitals,
)
from drlibre.reporting.application.ports.outbound import ActivityQueries
from drlibre.reporting.domain.available_minutes import Absence, RuleHours
from drlibre.reporting.infrastructure.sql_activity import SqlActivityQueries
from drlibre.scheduling.infrastructure.repositories import DjangoAvailabilityRules, DjangoTimeOffs
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders import stored_user
from tests.builders_booking import existing_appointment
from tests.builders_scheduling import rule, stored_profile, time_off
from tests.fakes.reporting import ActivityAppointment, ActivityClinician, InMemoryActivityQueries


@dataclass
class ActivityScene:
    """Writes the same activity to a fake or to PostgreSQL; times are local to the clinician."""

    queries: ActivityQueries
    clinician: Callable[[str, str, bool], Id]
    appointment: Callable[[Id, datetime, int, str, str], Id]
    rule: Callable[[Id, int, time, time], None]
    off: Callable[[Id, datetime, datetime], None]
    waitlist: Callable[[str], None]
    zones: dict[Id, ZoneInfo] = field(default_factory=dict)

    def at(self, clinician: Id, local: datetime) -> datetime:
        return local.replace(tzinfo=self.zones[clinician])


def fake_activity() -> ActivityScene:
    fake = InMemoryActivityQueries()
    names: dict[Id, str] = {}
    scene: ActivityScene

    def clinician(name: str, zone: str, active: bool) -> Id:
        clinician_id = Id()
        names[clinician_id] = name
        scene.zones[clinician_id] = ZoneInfo(zone)
        fake.clinicians[clinician_id] = ActivityClinician(time_zone=zone, active=active)
        return clinician_id

    def appointment(
        clinician_id: Id, local: datetime, minutes: int, status: str, source: str
    ) -> Id:
        start = scene.at(clinician_id, local)
        zone = fake.clinicians[clinician_id].time_zone
        end = start + timedelta(minutes=minutes)
        fake.appointments.append(
            ActivityAppointment(clinician_id, names[clinician_id], zone, start, end, status, source)
        )
        return Id()

    def add_rule(clinician_id: Id, weekday: int, start: time, end: time) -> None:
        valid_from = datetime(2026, 1, 1).date()
        fake.clinicians[clinician_id].rules.append(RuleHours(weekday, start, end, valid_from, None))

    def off(clinician_id: Id, start: datetime, end: datetime) -> None:
        fake.clinicians[clinician_id].absences.append(
            Absence(scene.at(clinician_id, start), scene.at(clinician_id, end))
        )

    scene = ActivityScene(fake, clinician, appointment, add_rule, off, fake.waitlist.append)
    return scene


def real_activity() -> ActivityScene:
    departments: dict[str, tuple[Department, Id]] = {}
    scene: ActivityScene

    def department_of(zone: str) -> tuple[Department, Id]:
        if zone not in departments:
            hospital = dataclasses.replace(build.hospital(), time_zone=zone)
            DjangoHospitals().save(hospital)
            department = build.department(hospital.id)
            DjangoDepartments().save(department)
            kind = build.appointment_type(department.id)
            DjangoAppointmentTypes().save(kind)
            departments[zone] = (department, kind.id)
        return departments[zone]

    kinds: dict[Id, Id] = {}

    def clinician(name: str, zone: str, active: bool) -> Id:
        department, kind = department_of(zone)
        user = dataclasses.replace(stored_user(Role.CLINICIAN), full_name=name, active=active)
        DjangoUsers().save(user)
        profile = stored_profile(department, user_id=user.id)
        scene.zones[profile.id] = ZoneInfo(zone)
        kinds[profile.id] = kind
        return profile.id

    def appointment(
        clinician_id: Id, local: datetime, minutes: int, status: str, source: str
    ) -> Id:
        start = scene.at(clinician_id, local)
        booked = existing_appointment(
            patient_id=Id(),
            clinician_id=clinician_id,
            appointment_type_id=kinds[clinician_id],
            start=start,
            end=start + timedelta(minutes=minutes),
            status=AppointmentStatus(status),
            source=Source(source),
        )
        DjangoAppointments().add(booked)
        return booked.id

    def add_rule(clinician_id: Id, weekday: int, start: time, end: time) -> None:
        DjangoAvailabilityRules().save(rule(clinician_id, weekday=weekday, start=start, end=end))

    def off(clinician_id: Id, start: datetime, end: datetime) -> None:
        DjangoTimeOffs().save(
            time_off(clinician_id, scene.at(clinician_id, start), scene.at(clinician_id, end))
        )

    def waitlist(status: str) -> None:
        kind = next(iter(departments.values()))[1]
        offered = None
        if status == "OFFERED":
            # A cancelled appointment outside every range carries the offer.
            offered = appointment(
                next(iter(kinds)), datetime(2027, 6, 1, 9), 30, "CANCELLED", "ONLINE"
            )
        now = datetime(2026, 11, 1, tzinfo=UTC)
        WaitlistEntryRecord.objects.create(
            patient_id=uuid.uuid4(),
            appointment_type_id=kind.value,
            earliest=now,
            latest=now + timedelta(days=30),
            status=status,
            created_at=now,
            offered_appointment_id=offered.value if offered else None,
        )

    scene = ActivityScene(SqlActivityQueries(), clinician, appointment, add_rule, off, waitlist)
    return scene
