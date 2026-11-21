import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from drlibre.booking.infrastructure.django.models import BookingHoldRecord
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.organisation.infrastructure.django.models import (
    AppointmentTypeRecord,
    ClinicianProfileRecord,
    DepartmentRecord,
    HospitalRecord,
    SpecialtyRecord,
)
from drlibre.scheduling.infrastructure.django.models import SlotModel

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


def _code(prefix: str) -> str:
    return f"{prefix}{uuid.uuid4().hex[:10].upper()}"


@dataclass
class SearchWorld:
    """Reference data and stored slots written straight to PostgreSQL, rolled back per test."""

    hospitals: dict[str, HospitalRecord] = field(default_factory=dict)
    departments: dict[str, DepartmentRecord] = field(default_factory=dict)
    types: dict[str, AppointmentTypeRecord] = field(default_factory=dict)
    specialties: dict[str, SpecialtyRecord] = field(default_factory=dict)
    clinicians: dict[str, ClinicianProfileRecord] = field(default_factory=dict)

    def hospital(
        self,
        name: str,
        city: str,
        *,
        latitude: float | None = None,
        longitude: float | None = None,
        time_zone: str = "Europe/Paris",
    ) -> HospitalRecord:
        record = HospitalRecord.objects.create(
            name=name,
            code=_code("H"),
            description=f"Description de {name}",
            street="1 rue de la Paix",
            postal_code="59000",
            city=city,
            country="France",
            phone="+33 3 20 00 00 00",
            time_zone=time_zone,
            latitude=latitude,
            longitude=longitude,
            created_at=NOW,
            updated_at=NOW,
        )
        self.hospitals[name] = record
        return record

    def department(self, name: str, hospital: str) -> DepartmentRecord:
        record = DepartmentRecord.objects.create(
            hospital=self.hospitals[hospital],
            name=name,
            code=_code("D"),
            created_at=NOW,
            updated_at=NOW,
        )
        self.departments[name] = record
        return record

    def appointment_type(
        self, name: str, department: str, minutes: int, *, online: bool = True, buffer: int = 0
    ) -> AppointmentTypeRecord:
        record = AppointmentTypeRecord.objects.create(
            department=self.departments[department],
            name=name,
            code=_code("T"),
            duration_minutes=minutes,
            buffer_minutes=buffer,
            colour="#336699",
            needs_room=False,
            bookable_online=online,
            created_at=NOW,
            updated_at=NOW,
        )
        self.types[name] = record
        return record

    def specialty(self, name: str) -> SpecialtyRecord:
        if name not in self.specialties:
            self.specialties[name] = SpecialtyRecord.objects.create(
                name=name, code=_code("S"), created_at=NOW, updated_at=NOW
            )
        return self.specialties[name]

    def clinician(self, name: str, specialty: str, department: str) -> ClinicianProfileRecord:
        user = UserRecord.objects.create(
            email=f"{uuid.uuid4().hex[:12]}@example.org",
            full_name=name,
            role="CLINICIAN",
            phone="0600000000",
            birth_date=date(1975, 1, 1),
            created_at=NOW,
            updated_at=NOW,
        )
        record = ClinicianProfileRecord.objects.create(
            user_id=user.id,
            department=self.departments[department],
            specialty=self.specialty(specialty),
            title="Médecin",
            created_at=NOW,
            updated_at=NOW,
        )
        self.clinicians[name] = record
        return record

    def zone_of(self, clinician: ClinicianProfileRecord) -> ZoneInfo:
        return ZoneInfo(clinician.department.hospital.time_zone)

    def local(self, clinician: ClinicianProfileRecord, raw: str) -> datetime:
        return datetime.fromisoformat(raw).replace(tzinfo=self.zone_of(clinician))

    def free(self, name: str, starts: list[str], type_name: str | None = None) -> None:
        clinician = self.clinicians[name]
        kind = (
            self.types[type_name]
            if type_name
            else min(
                (t for t in self.types.values() if t.department_id == clinician.department_id),
                key=lambda t: t.duration_minutes,
            )
        )
        for raw in starts:
            start = self.local(clinician, raw)
            SlotModel.objects.create(
                clinician=clinician,
                appointment_type=kind,
                start=start,
                end=start + timedelta(minutes=kind.duration_minutes),
            )

    def hold(self, name: str, start: str, *, minutes_left: int) -> None:
        clinician = self.clinicians[name]
        kind = min(
            (t for t in self.types.values() if t.department_id == clinician.department_id),
            key=lambda t: t.duration_minutes,
        )
        begin = self.local(clinician, start)
        BookingHoldRecord.objects.create(
            clinician=clinician,
            appointment_type=kind,
            start=begin,
            end=begin + timedelta(minutes=kind.duration_minutes),
            source="ONLINE",
            full_name="Visiteur Test",
            birth_date=date(1990, 1, 1),
            email="visiteur@example.org",
            expires_at=NOW + timedelta(minutes=minutes_left),
        )
