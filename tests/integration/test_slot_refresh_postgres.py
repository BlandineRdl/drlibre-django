import dataclasses
from datetime import UTC, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from drlibre.audit.application.ports.outbound import AuditEntry
from drlibre.audit.infrastructure.unit_of_work import DjangoUnitOfWork
from drlibre.booking.infrastructure.queries import DjangoBookingQueries
from drlibre.bootstrap.container import Container, real_adapters, wire
from drlibre.organisation.domain.department import Department
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoDepartments,
    DjangoHospitals,
)
from drlibre.scheduling.application.use_cases.refresh_slots import RefreshSlotsUseCase
from drlibre.scheduling.domain.slot import Period, Slot
from drlibre.scheduling.infrastructure.booking_appointments import BookingClinicianAppointments
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel, SlotModel
from drlibre.scheduling.infrastructure.repositories import DjangoAvailabilityRules, DjangoTimeOffs
from drlibre.scheduling.infrastructure.slot_queries import DjangoSlotQueries
from drlibre.scheduling.infrastructure.slot_store import DjangoSlotStore
from drlibre.shared_kernel.ids import Id
from tests import builders_organisation as build
from tests.builders_scheduling import rule, stored_department, stored_profile
from tests.fakes.audit_log import AuditLogUnavailableError, InMemoryAuditLog
from tests.fakes.clock import FixedClock

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

PARIS = ZoneInfo("Europe/Paris")
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


def refresh_slots(clock: FixedClock) -> RefreshSlotsUseCase:
    return RefreshSlotsUseCase(
        clock=clock,
        directory=real_adapters().scheduling_directory,
        rules=DjangoAvailabilityRules(),
        time_offs=DjangoTimeOffs(),
        appointments=BookingClinicianAppointments(DjangoBookingQueries()),
        store=DjangoSlotStore(),
    )


def stored_type(department: Department) -> Id:
    kind = build.appointment_type(department.id)
    DjangoAppointmentTypes().save(kind)
    return kind.id


def read(kind: Id, clinician: Id, start: datetime, end: datetime) -> tuple[Slot, ...]:
    found = DjangoSlotQueries().free_slots(
        kind, (clinician,), within=Period(start, end), not_before=NOW
    )
    return tuple(f.slot for f in found)


def test_an_audit_failure_rolls_back_the_rule_and_its_slots_together() -> None:
    """Règle : chaque écriture est auditée dans sa transaction, ses créneaux avec elle."""
    department = stored_department()
    stored_type(department)
    profile = stored_profile(department)
    made = rule(profile.id, weekday=1)

    stored_inside: list[bool] = []

    def write_refresh_then_fail_to_audit() -> None:
        with DjangoUnitOfWork():
            DjangoAvailabilityRules().save(made)
            refresh_slots(FixedClock(NOW)).execute(clinician_id=profile.id)
            stored_inside.append(SlotModel.objects.filter(clinician_id=profile.id.value).exists())
            InMemoryAuditLog(failing=True).record(
                AuditEntry.from_event(
                    actor=None,
                    action="availability_rule.created",
                    entity_type="availability_rule",
                    entity_id=made.id,
                    at=NOW,
                )
            )

    with pytest.raises(AuditLogUnavailableError):
        write_refresh_then_fail_to_audit()

    assert stored_inside == [True]
    assert not AvailabilityRuleModel.objects.filter(id=made.id.value).exists()
    assert not SlotModel.objects.filter(clinician_id=profile.id.value).exists()


def type_fields(department: Department, code: str, minutes: int) -> dict[str, str]:
    return {
        "name": "Consultation",
        "code": code,
        "department_id": str(department.id),
        "duration_minutes": str(minutes),
        "buffer_minutes": "0",
        "colour": "#336699",
        "active": "on",
    }


def test_editing_a_types_duration_changes_its_department_slots_in_the_same_response() -> None:
    """Modifier la durée d'un type change les créneaux de son département dans la même réponse."""
    app: Container = wire(dataclasses.replace(real_adapters(), clock=FixedClock(NOW)))
    department = stored_department()
    profile = stored_profile(department)
    code = build.code("T")
    kind = app.save_appointment_type.execute(
        actor=None, record_id=None, fields=type_fields(department, code, 30)
    )
    app.save_availability_rule.execute(
        actor=profile.user_id,
        rule_id=None,
        fields={"weekday": "1", "start": "09:00", "end": "10:00", "step_minutes": "30"},
    )
    monday = datetime(2026, 11, 23, tzinfo=PARIS)
    assert len(read(kind, profile.id, monday, monday + timedelta(days=1))) == 2

    app.save_appointment_type.execute(
        actor=None, record_id=kind, fields=type_fields(department, code, 60)
    )

    (slot,) = read(kind, profile.id, monday, monday + timedelta(days=1))
    assert slot.end - slot.start == timedelta(minutes=60)


def test_slots_keep_their_local_hour_across_the_spring_time_change() -> None:
    """Story plages : pour chaque jour local de la période, au changement d'heure de mars."""
    department = stored_department()
    kind = stored_type(department)
    profile = stored_profile(department)
    rules = DjangoAvailabilityRules()
    for weekday in range(7):
        rules.save(rule(profile.id, weekday=weekday, start=time(9), end=time(9, 30)))
    refresh_slots(FixedClock(datetime(2027, 3, 1, tzinfo=UTC))).execute(clinician_id=profile.id)

    found = read(
        kind, profile.id, datetime(2027, 3, 27, tzinfo=PARIS), datetime(2027, 3, 30, tzinfo=PARIS)
    )

    assert [s.start.astimezone(PARIS).time() for s in found] == [time(9)] * 3
    assert [s.start.astimezone(UTC).hour for s in found] == [8, 7, 7]


def test_a_deleted_clinician_profile_leaves_no_slot() -> None:
    """Supprimer un profil praticien retire ses créneaux avec ses plages et ses absences."""
    app: Container = wire(dataclasses.replace(real_adapters(), clock=FixedClock(NOW)))
    department = stored_department()
    stored_type(department)
    profile = stored_profile(department)
    DjangoAvailabilityRules().save(rule(profile.id, weekday=1))
    refresh_slots(FixedClock(NOW)).execute(clinician_id=profile.id)
    assert SlotModel.objects.filter(clinician_id=profile.id.value).exists()

    app.delete_clinician_profile.execute(actor=None, profile_id=profile.id)

    assert not SlotModel.objects.filter(clinician_id=profile.id.value).exists()


def first_local_start(kind: Id, profile: Id, zone: str) -> time:
    tz = ZoneInfo(zone)
    monday = datetime(2026, 11, 23, tzinfo=tz)
    (slot, *_) = read(kind, profile, monday, monday + timedelta(days=1))
    return slot.start.astimezone(tz).time()


def ruled_profile(department: Department) -> tuple[Id, Id]:
    kind = stored_type(department)
    profile = stored_profile(department)
    DjangoAvailabilityRules().save(rule(profile.id, weekday=1, start=time(9), end=time(10)))
    refresh_slots(FixedClock(NOW)).execute(clinician_id=profile.id)
    assert first_local_start(kind, profile.id, "Europe/Paris") == time(9)
    return kind, profile.id


def test_changing_a_hospitals_time_zone_moves_its_clinicians_slots_in_the_same_response() -> None:
    """Règle §4 : la disponibilité est en heure locale de l'hôpital, son fuseau changé compris."""
    app: Container = wire(dataclasses.replace(real_adapters(), clock=FixedClock(NOW)))
    department = stored_department()
    kind, profile = ruled_profile(department)
    hospital = DjangoHospitals().get(department.hospital_id)
    assert hospital is not None
    fields = {
        "name": hospital.name,
        "code": hospital.code,
        "street": hospital.street,
        "postal_code": hospital.postal_code,
        "city": hospital.city,
        "country": hospital.country,
        "phone": hospital.phone,
        "time_zone": "America/New_York",
        "active": "on",
    }

    app.save_hospital.execute(actor=None, record_id=hospital.id, fields=fields)

    assert first_local_start(kind, profile, "America/New_York") == time(9)


def test_moving_a_department_to_another_hospital_moves_its_clinicians_slots() -> None:
    """Règle §4 : la disponibilité suit le fuseau du nouvel hôpital du département."""
    app: Container = wire(dataclasses.replace(real_adapters(), clock=FixedClock(NOW)))
    department = stored_department()
    kind, profile = ruled_profile(department)
    elsewhere = dataclasses.replace(build.hospital(), time_zone="America/New_York")
    DjangoHospitals().save(elsewhere)
    fields = {"name": department.name, "code": department.code, "hospital_id": str(elsewhere.id)}

    app.save_department.execute(actor=None, record_id=department.id, fields=fields)

    moved = DjangoDepartments().get(department.id)
    assert moved is not None
    assert moved.hospital_id == elsewhere.id
    assert first_local_start(kind, profile, "America/New_York") == time(9)
