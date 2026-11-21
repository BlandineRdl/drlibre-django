from collections.abc import Callable

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.outbound import (
    Appointments,
    BookingDirectory,
    ScheduleLocks,
    SlotRefresh,
    Staff,
)
from drlibre.booking.application.use_cases.actor_scope import (
    actor_scope,
    locked_scoped_appointment,
)
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class StatusChange:
    """Spec 5.6 steps every staff status change runs; the patient is never notified."""

    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        directory: BookingDirectory,
        staff: Staff,
        appointments: Appointments,
        locks: ScheduleLocks,
        slot_refresh: SlotRefresh,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._directory = directory
        self._staff = staff
        self._appointments = appointments
        self._locks = locks
        self._slot_refresh = slot_refresh

    def apply(
        self,
        *,
        actor_id: Id,
        appointment_id: Id,
        transition: Callable[[Appointment], Appointment],
    ) -> Appointment:
        with self._uow:
            scope = actor_scope(self._directory, self._staff, actor_id)
            scope.require_staff()
            current = locked_scoped_appointment(
                scope, self._appointments, self._locks, appointment_id
            )
            changed = transition(current)
            self._appointments.save(changed)
            # A no-show frees its slot.
            if not changed.active:
                self._slot_refresh.refresh(changed.clinician_id)
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor_id,
                    action="booking.appointment_status_changed",
                    entity_type="appointment",
                    entity_id=changed.id,
                    at=self._clock.now(),
                    metadata={"from": current.status, "to": changed.status},
                )
            )
            return changed
