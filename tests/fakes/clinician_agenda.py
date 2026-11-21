import dataclasses
from datetime import datetime

from drlibre.booking.application.ports.outbound import (
    ClinicianAgenda,
    ClinicianEntry,
    ClinicianFilter,
    ClinicianPatient,
    RoomBooking,
    RoomLabel,
    RoomsDay,
)
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest
from tests.fakes.booking import FixedBookingDirectory, InMemoryAppointments, InMemoryHolds
from tests.fakes.scheduling import InMemorySlotStore
from tests.fakes.users import InMemoryUsers

_UPCOMING = (AppointmentStatus.BOOKED, AppointmentStatus.CHECKED_IN)


class InMemoryClinicianAgenda(ClinicianAgenda):
    """Joins in-memory appointments to users, the directory's rooms, `labels` and `colours`."""

    def __init__(
        self,
        *,
        appointments: InMemoryAppointments,
        users: InMemoryUsers,
        directory: FixedBookingDirectory,
        slots: InMemorySlotStore,
        holds: InMemoryHolds,
    ) -> None:
        self.appointments = appointments
        self.users = users
        self.directory = directory
        self.slots = slots
        self.holds = holds
        # Names of types and rooms, colours of types.
        self.labels: dict[Id, str] = {}
        self.colours: dict[Id, str] = {}

    def entries(
        self, clinician_id: Id, agenda_filter: ClinicianFilter
    ) -> tuple[ClinicianEntry, ...]:
        f = agenda_filter
        rows = sorted(
            (
                a
                for a in self.appointments.rows
                if a.clinician_id == clinician_id
                and f.patient_id in (None, a.patient_id)
                and f.status in (None, a.status)
                and (f.start is None or a.start >= f.start)
                and (f.end is None or a.start < f.end)
            ),
            key=lambda a: a.start,
        )
        return tuple(self._entry(dataclasses.replace(a, clinical_notes=None)) for a in rows)

    def detail(self, appointment_id: Id) -> ClinicianEntry | None:
        found = self.appointments.get(appointment_id)
        return self._entry(found) if found else None

    def patients(
        self, clinician_id: Id, request: PageRequest, now: datetime
    ) -> Page[ClinicianPatient]:
        own = [a for a in self.appointments.rows if a.clinician_id == clinician_id]
        search = request.search.casefold()
        found = sorted(
            (
                self._patient(patient_id, [a for a in own if a.patient_id == patient_id], now)
                for patient_id in {a.patient_id for a in own}
                if search in self.users.rows[patient_id].full_name.casefold()
            ),
            key=lambda p: (p.full_name, str(p.patient_id)),
        )
        items = tuple(found[request.offset : request.offset + PAGE_SIZE])
        return Page(items=items, total=len(found), number=request.number)

    def room_day(self, clinician_id: Id, start: datetime, end: datetime) -> RoomsDay:
        clinician = self.directory.clinician(clinician_id)
        room_ids = self.directory.rooms(clinician.department_id) if clinician else ()
        bookings = sorted(
            (
                RoomBooking(
                    a.room_id,
                    a.start,
                    a.end,
                    self._name(a.patient_id) if a.clinician_id == clinician_id else None,
                )
                for a in self.appointments.rows
                if a.active
                and a.room_id in room_ids
                and a.start < end
                and start < a.end
                and a.room_id is not None
            ),
            key=lambda b: (b.start, room_ids.index(b.room_id)),
        )
        rooms = tuple(RoomLabel(r, self.labels.get(r, "")) for r in room_ids)
        return RoomsDay(rooms=rooms, bookings=tuple(bookings))

    def next_free_slot(self, clinician_id: Id, after: datetime, now: datetime) -> datetime | None:
        starts = (
            r.slot.start
            for r in self.slots.rows
            if r.clinician_id == clinician_id
            and r.slot.start >= after
            and not self.holds.held(clinician_id, r.slot.start, r.slot.end, at=now, excluding=None)
        )
        return min(starts, default=None)

    def _name(self, patient_id: Id) -> str:
        return self.users.rows[patient_id].full_name

    def _entry(self, appointment: Appointment) -> ClinicianEntry:
        patient = self.users.rows[appointment.patient_id]
        return ClinicianEntry(
            appointment=appointment,
            patient_name=patient.full_name,
            patient_phone=patient.phone,
            patient_birth_date=patient.birth_date,
            appointment_type=self.labels.get(appointment.appointment_type_id, ""),
            type_colour=self.colours.get(appointment.appointment_type_id, ""),
            room=self.labels.get(appointment.room_id) if appointment.room_id else None,
        )

    def _patient(self, patient_id: Id, rows: list[Appointment], now: datetime) -> ClinicianPatient:
        patient = self.users.rows[patient_id]
        past = [a.start for a in rows if a.status is AppointmentStatus.COMPLETED and a.start < now]
        future = [a.start for a in rows if a.status in _UPCOMING and a.start > now]
        return ClinicianPatient(
            patient_id=patient_id,
            full_name=patient.full_name,
            phone=patient.phone,
            last_visit=max(past, default=None),
            next_visit=min(future, default=None),
        )
