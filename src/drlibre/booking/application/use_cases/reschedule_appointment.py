from datetime import datetime, timedelta

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import Appointment, RescheduleAppointment
from drlibre.booking.application.ports.outbound import (
    Appointments,
    BookingDirectory,
    BookingNotices,
    FreeSlots,
    ScheduleLocks,
    SlotRefresh,
)
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.application.use_cases.view_appointment import own_appointment
from drlibre.booking.domain import booking_rules
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class RescheduleAppointmentUseCase(RescheduleAppointment):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        appointments: Appointments,
        directory: BookingDirectory,
        free_slots: FreeSlots,
        placement: Placement,
        locks: ScheduleLocks,
        slot_refresh: SlotRefresh,
        notices: BookingNotices,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._appointments = appointments
        self._directory = directory
        self._free_slots = free_slots
        self._placement = placement
        self._locks = locks
        self._slot_refresh = slot_refresh
        self._notices = notices

    def execute(self, *, appointment_id: Id, patient_id: Id, start: datetime) -> Appointment:
        with self._uow:
            found = own_appointment(self._appointments, appointment_id, patient_id)
            self._locks.lock_clinician(found.clinician_id)
            self._locks.lock_patient(found.patient_id)
            # Read again under the locks, so a change committed meanwhile is seen.
            current = own_appointment(self._appointments, appointment_id, patient_id)
            current.require_movable()
            kind = self._directory.appointment_type(current.appointment_type_id)
            clinician = self._directory.clinician(current.clinician_id)
            if kind is None or clinician is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")
            end = start + timedelta(minutes=kind.duration_minutes)
            self._placement.refuse_conflicts(
                patient_id, clinician.id, start, end, ignoring_hold=None, excluding=current.id
            )
            now = self._clock.now()
            broken = booking_rules.reschedule_violations(
                for_patient=True,
                current_start=current.start,
                new_start=start,
                now=now,
                type_online=kind.bookable_online,
                is_free_slot=self._free_slots.is_free(
                    clinician.id,
                    kind.id,
                    start,
                    ignoring_hold=None,
                    ignoring_appointment=current.id,
                ),
            )
            if broken:
                raise DomainError(
                    ErrorCode.RULE_VIOLATION,
                    "Le déplacement enfreint une règle.",
                    {"rules": [rule.value for rule in broken]},
                )
            room = self._placement.room(
                kind, clinician, start, end, current=current.room_id, excluding=current.id
            )
            moved = current.moved(start=start, duration=end - start, room_id=room)
            self._appointments.save(moved)
            self._slot_refresh.refresh(moved.clinician_id)
            self._audit.record(self._rescheduled_entry(moved, patient_id, now))
            self._notices.rescheduled(moved)
            return moved

    def _rescheduled_entry(self, moved: Appointment, actor: Id, at: datetime) -> AuditEntry:
        metadata: dict[str, object] = {"clinician_id": moved.clinician_id}
        if moved.room_id is not None:
            metadata["room_id"] = moved.room_id
        return AuditEntry.from_event(
            actor=actor,
            action="booking.appointment_rescheduled",
            entity_type="appointment",
            entity_id=moved.id,
            at=at,
            metadata=metadata,
        )
