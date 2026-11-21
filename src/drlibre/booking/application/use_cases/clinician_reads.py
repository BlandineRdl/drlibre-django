import dataclasses
from datetime import date, datetime, time, timedelta
from itertools import groupby
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.inbound import (
    AgendaHour,
    AppointmentFile,
    ClinicianAppointment,
    ClinicianDay,
    ClinicianDayView,
    ClinicianEntry,
    ClinicianFilter,
    ClinicianPatient,
    ClinicianPatients,
    ClinicianWeek,
    ClinicianWeekView,
    DayCounts,
    DepartmentRoomsDay,
    HistoryActor,
    HistoryLine,
    ListClinicianAppointments,
    RoomsDayView,
)
from drlibre.booking.application.ports.outbound import (
    AppointmentHistory,
    Appointments,
    BookingDirectory,
    ClinicianAgenda,
)
from drlibre.booking.application.use_cases.own_clinician_appointment import (
    clinician_profile,
    own_clinician_appointment,
)
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.booking.domain.booking_rules import clinician_actions
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest

ONE_DAY = timedelta(days=1)


def _time_zone(directory: BookingDirectory, profile_id: Id) -> str:
    venue = directory.venue(profile_id)
    if venue is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Praticien introuvable.")
    return venue.time_zone


def _day_bounds(day: date, zone: ZoneInfo) -> tuple[datetime, datetime]:
    return datetime.combine(day, time(), zone), datetime.combine(day + ONE_DAY, time(), zone)


def _with_actions(entry: ClinicianEntry) -> ClinicianEntry:
    return dataclasses.replace(entry, actions=clinician_actions(entry.appointment))


def _count(entries: tuple[ClinicianEntry, ...], status: AppointmentStatus) -> int:
    return sum(1 for e in entries if e.appointment.status is status)


def _age(birth: date | None, today: date) -> int | None:
    if birth is None:
        return None
    return today.year - birth.year - ((today.month, today.day) < (birth.month, birth.day))


def _actor(entry_actor: Id | None, appointment: Appointment, clinician_user: Id) -> HistoryActor:
    if entry_actor == appointment.patient_id:
        return HistoryActor.PATIENT
    if entry_actor == clinician_user:
        return HistoryActor.CLINICIAN
    return HistoryActor.STAFF


class ClinicianDayUseCase(ClinicianDay):
    def __init__(
        self, *, clock: Clock, directory: BookingDirectory, agenda: ClinicianAgenda
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._agenda = agenda

    def execute(self, *, actor_id: Id, day: date | None) -> ClinicianDayView:
        profile_id = clinician_profile(self._directory, actor_id)
        time_zone = _time_zone(self._directory, profile_id)
        zone = ZoneInfo(time_zone)
        now = self._clock.now()
        shown = day or now.astimezone(zone).date()
        start, end = _day_bounds(shown, zone)
        found = self._agenda.entries(profile_id, ClinicianFilter(start=start, end=end))
        entries = tuple(_with_actions(e) for e in found)
        hours = tuple(
            AgendaHour(hour, tuple(group))
            for hour, group in groupby(
                entries, key=lambda e: e.appointment.start.astimezone(zone).hour
            )
        )
        counts = DayCounts(
            appointments=len(entries) - _count(entries, AppointmentStatus.CANCELLED),
            cancelled=_count(entries, AppointmentStatus.CANCELLED),
            completed=_count(entries, AppointmentStatus.COMPLETED),
            no_show=_count(entries, AppointmentStatus.NO_SHOW),
        )
        next_free = self._agenda.next_free_slot(profile_id, max(now, start), now)
        return ClinicianDayView(shown, time_zone, hours, counts, next_free)


class ClinicianWeekUseCase(ClinicianWeek):
    def __init__(
        self, *, clock: Clock, directory: BookingDirectory, agenda: ClinicianAgenda
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._agenda = agenda

    def execute(self, *, actor_id: Id, week: date | None) -> ClinicianWeekView:
        profile_id = clinician_profile(self._directory, actor_id)
        time_zone = _time_zone(self._directory, profile_id)
        zone = ZoneInfo(time_zone)
        asked = week or self._clock.now().astimezone(zone).date()
        monday = asked - timedelta(days=asked.weekday())
        start = datetime.combine(monday, time(), zone)
        end = datetime.combine(monday + 7 * ONE_DAY, time(), zone)
        found = self._agenda.entries(profile_id, ClinicianFilter(start=start, end=end))
        active = tuple(e for e in found if e.appointment.active)
        return ClinicianWeekView(monday, time_zone, active)


class ClinicianAppointmentUseCase(ClinicianAppointment):
    def __init__(
        self,
        *,
        clock: Clock,
        directory: BookingDirectory,
        appointments: Appointments,
        agenda: ClinicianAgenda,
        history: AppointmentHistory,
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._appointments = appointments
        self._agenda = agenda
        self._history = history

    def execute(self, *, actor_id: Id, appointment_id: Id) -> AppointmentFile:
        profile_id = clinician_profile(self._directory, actor_id)
        own_clinician_appointment(self._appointments, appointment_id, profile_id)
        entry = self._agenda.detail(appointment_id)
        if entry is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")
        time_zone = _time_zone(self._directory, profile_id)
        today = self._clock.now().astimezone(ZoneInfo(time_zone)).date()
        # The guard proved the actor is the appointment's clinician user.
        history = tuple(
            HistoryLine(h.action, _actor(h.actor_id, entry.appointment, actor_id), h.at)
            for h in self._history.entries_of(appointment_id)
        )
        return AppointmentFile(
            entry=_with_actions(entry),
            time_zone=time_zone,
            patient_age=_age(entry.patient_birth_date, today),
            history=history,
        )


class ClinicianPatientsUseCase(ClinicianPatients):
    def __init__(
        self, *, clock: Clock, directory: BookingDirectory, agenda: ClinicianAgenda
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._agenda = agenda

    def execute(self, *, actor_id: Id, request: PageRequest) -> Page[ClinicianPatient]:
        profile_id = clinician_profile(self._directory, actor_id)
        return self._agenda.patients(profile_id, request, self._clock.now())


class DepartmentRoomsDayUseCase(DepartmentRoomsDay):
    def __init__(
        self, *, clock: Clock, directory: BookingDirectory, agenda: ClinicianAgenda
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._agenda = agenda

    def execute(self, *, actor_id: Id, day: date | None) -> RoomsDayView:
        profile_id = clinician_profile(self._directory, actor_id)
        time_zone = _time_zone(self._directory, profile_id)
        zone = ZoneInfo(time_zone)
        shown = day or self._clock.now().astimezone(zone).date()
        start, end = _day_bounds(shown, zone)
        found = self._agenda.room_day(profile_id, start, end)
        return RoomsDayView(shown, time_zone, found.rooms, found.bookings)


class ListClinicianAppointmentsUseCase(ListClinicianAppointments):
    def __init__(self, *, directory: BookingDirectory, agenda: ClinicianAgenda) -> None:
        self._directory = directory
        self._agenda = agenda

    def execute(
        self, *, actor_id: Id, agenda_filter: ClinicianFilter
    ) -> tuple[ClinicianEntry, ...]:
        profile_id = clinician_profile(self._directory, actor_id)
        return tuple(_with_actions(e) for e in self._agenda.entries(profile_id, agenda_filter))
