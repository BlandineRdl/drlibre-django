from datetime import UTC, date, datetime

from drlibre.booking.application.ports.outbound import BookableClinician, BookableType, Venue
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.identity.domain.user import Email, Role, User
from drlibre.shared_kernel.ids import Id


def bookable_type(
    department_id: Id,
    *,
    needs_room: bool = True,
    bookable_online: bool = True,
    active: bool = True,
    duration_minutes: int = 30,
) -> BookableType:
    return BookableType(
        id=Id(),
        department_id=department_id,
        duration_minutes=duration_minutes,
        needs_room=needs_room,
        bookable_online=bookable_online,
        active=active,
    )


def bookable_clinician(
    department_id: Id,
    *,
    weight: int = 1,
    default_room_id: Id | None = None,
    last_assigned_at: datetime | None = None,
    active: bool = True,
) -> BookableClinician:
    return BookableClinician(
        id=Id(),
        department_id=department_id,
        active=active,
        default_room_id=default_room_id,
        weight=weight,
        last_assigned_at=last_assigned_at,
    )


def existing_appointment(
    *,
    patient_id: Id,
    clinician_id: Id,
    start: datetime,
    end: datetime,
    room_id: Id | None = None,
    source: Source = Source.ONLINE,
    status: AppointmentStatus = AppointmentStatus.BOOKED,
) -> Appointment:
    return Appointment(
        id=Id(),
        patient_id=patient_id,
        clinician_id=clinician_id,
        appointment_type_id=Id(),
        room_id=room_id,
        start=start,
        end=end,
        status=status,
        source=source,
    )


def booking_venue(provider_name: str = "Dr Test") -> Venue:
    return Venue(
        hospital_name="Hôpital Test", time_zone="Europe/Paris", provider_name=provider_name
    )


def patient_user(
    patient_id: Id,
    *,
    email: str = "patient@example.org",
    role: Role = Role.PATIENT,
    active: bool = True,
    password_hash: str | None = None,
) -> User:
    at = datetime(2026, 1, 1, tzinfo=UTC)
    return User(
        id=patient_id,
        email=Email(email),
        full_name="Patient Test",
        role=role,
        active=active,
        password_hash=password_hash,
        must_change_password=False,
        last_login_at=None,
        created_at=at,
        updated_at=at,
        phone="0600000000",
        birth_date=date(1980, 1, 1),
    )
