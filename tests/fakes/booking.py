from datetime import datetime

from drlibre.booking.application.ports.outbound import (
    Appointments,
    BookableClinician,
    BookableType,
    BookingDirectory,
    BookingNotices,
    FreeSlots,
    Patients,
    RoundRobinLedger,
    ScheduleLocks,
    SlotRefresh,
)
from drlibre.booking.domain.appointment import Appointment, Source
from drlibre.shared_kernel.ids import Id


class InMemoryAppointments(Appointments):
    def __init__(self) -> None:
        self.rows: list[Appointment] = []

    def add(self, appointment: Appointment) -> None:
        self.rows.append(appointment)

    def conflicting_resources(
        self, *, clinician_id: Id, patient_id: Id, start: datetime, end: datetime
    ) -> tuple[str, ...]:
        overlapping = [a for a in self.rows if a.active and a.start < end and start < a.end]
        resources = (
            ("clinician", any(a.clinician_id == clinician_id for a in overlapping)),
            ("patient", any(a.patient_id == patient_id for a in overlapping)),
        )
        return tuple(name for name, hit in resources if hit)

    def open_online_count(self, patient_id: Id, now: datetime) -> int:
        online = (Source.ONLINE, Source.ROUND_ROBIN)
        return sum(
            1
            for a in self.rows
            if a.patient_id == patient_id and a.active and a.source in online and a.start > now
        )

    def busy_rooms(self, room_ids: tuple[Id, ...], start: datetime, end: datetime) -> frozenset[Id]:
        return frozenset(
            a.room_id
            for a in self.rows
            if a.active
            and a.room_id in room_ids
            and a.room_id is not None
            and a.start < end
            and start < a.end
        )


class FixedBookingDirectory(BookingDirectory):
    def __init__(self) -> None:
        self.types: dict[Id, BookableType] = {}
        self.clinicians: dict[Id, BookableClinician] = {}
        self.department_rooms: dict[Id, tuple[Id, ...]] = {}

    def appointment_type(self, appointment_type_id: Id) -> BookableType | None:
        return self.types.get(appointment_type_id)

    def clinician(self, clinician_id: Id) -> BookableClinician | None:
        return self.clinicians.get(clinician_id)

    def rooms(self, department_id: Id) -> tuple[Id, ...]:
        return self.department_rooms.get(department_id, ())


class InMemoryFreeSlots(FreeSlots):
    """Free slots as (clinician, type, start) rows."""

    def __init__(self) -> None:
        self.free: set[tuple[Id, Id, datetime]] = set()

    def is_free(
        self,
        clinician_id: Id,
        appointment_type_id: Id,
        start: datetime,
        *,
        ignoring_hold: Id | None,
    ) -> bool:
        return (clinician_id, appointment_type_id, start) in self.free

    def candidates_at(self, appointment_type_id: Id, start: datetime) -> tuple[Id, ...]:
        return tuple(c for c, t, s in self.free if t == appointment_type_id and s == start)


class RecordingSlotRefresh(SlotRefresh):
    def __init__(self) -> None:
        self.refreshed: list[Id] = []

    def refresh(self, clinician_id: Id) -> None:
        self.refreshed.append(clinician_id)


class RecordingScheduleLocks(ScheduleLocks):
    def __init__(self) -> None:
        self.clinicians: list[Id] = []
        self.patients: list[Id] = []

    def lock_clinician(self, clinician_id: Id) -> None:
        self.clinicians.append(clinician_id)

    def lock_patient(self, patient_id: Id) -> None:
        self.patients.append(patient_id)


class InMemoryPatients(Patients):
    def __init__(self) -> None:
        self.active: set[Id] = set()

    def is_active(self, patient_id: Id) -> bool:
        return patient_id in self.active


class RecordingBookingNotices(BookingNotices):
    def __init__(self) -> None:
        self.confirmations: list[Appointment] = []

    def confirmed(self, appointment: Appointment) -> None:
        self.confirmations.append(appointment)


class InMemoryRoundRobinLedger(RoundRobinLedger):
    def __init__(self) -> None:
        self.assigned: dict[Id, datetime] = {}

    def record(self, clinician_id: Id, at: datetime) -> None:
        self.assigned[clinician_id] = at
