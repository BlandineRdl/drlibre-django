import uuid
from datetime import UTC, datetime

from drlibre.organisation.domain.appointment_type import AppointmentType
from drlibre.organisation.domain.department import Department
from drlibre.organisation.domain.hospital import Hospital
from drlibre.organisation.domain.room import Room
from drlibre.organisation.domain.specialty import Specialty
from drlibre.shared_kernel.ids import Id

AT = datetime(2026, 11, 20, 10, tzinfo=UTC)


def code(prefix: str = "C") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8].upper()}"


def hospital(*, name: str = "Hôpital Nord", code_value: str | None = None) -> Hospital:
    fields = {
        "name": name,
        "code": code_value or code("H"),
        "street": "1 rue de la Paix",
        "postal_code": "59000",
        "city": "Lille",
        "country": "France",
        "phone": "+33 3 20 00 00 00",
        "time_zone": "Europe/Paris",
        "latitude": "50.63",
        "active": "on",
    }
    return Hospital.from_form(fields, id=Id(), created_at=AT, at=AT)


def specialty() -> Specialty:
    fields = {"name": "Cardiologie", "code": code("S"), "active": "on"}
    return Specialty.from_form(fields, id=Id(), created_at=AT, at=AT)


def department(hospital_id: Id, *, name: str = "Cardiologie") -> Department:
    fields = {"name": name, "code": code("D"), "hospital_id": str(hospital_id)}
    return Department.from_form(fields, id=Id(), created_at=AT, at=AT)


def room(department_id: Id, *, name: str = "Salle 1", active: bool = True) -> Room:
    fields = {
        "name": name,
        "code": code("R"),
        "department_id": str(department_id),
        "floor": "1",
        "capacity": "2",
        "equipment": "ECG, Tensiomètre",
        "active": "on" if active else "",
    }
    return Room.from_form(fields, id=Id(), created_at=AT, at=AT)


def appointment_type(department_id: Id) -> AppointmentType:
    fields = {
        "name": "Consultation",
        "code": code("T"),
        "department_id": str(department_id),
        "duration_minutes": "30",
        "buffer_minutes": "0",
        "colour": "#336699",
        "needs_room": "on",
        "active": "on",
    }
    return AppointmentType.from_form(fields, id=Id(), created_at=AT, at=AT)
