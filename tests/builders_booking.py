from datetime import datetime

from drlibre.booking.application.ports.outbound import BookableClinician, BookableType
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
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
