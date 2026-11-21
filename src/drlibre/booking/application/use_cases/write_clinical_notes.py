from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import WriteClinicalNotes
from drlibre.booking.application.ports.outbound import Appointments, BookingDirectory, ScheduleLocks
from drlibre.booking.application.use_cases.actor_scope import (
    ActorKind,
    ActorScope,
    locked_scoped_appointment,
)
from drlibre.booking.application.use_cases.own_clinician_appointment import clinician_profile
from drlibre.booking.domain.appointment import Appointment
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class WriteClinicalNotesUseCase(WriteClinicalNotes):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        directory: BookingDirectory,
        appointments: Appointments,
        locks: ScheduleLocks,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._directory = directory
        self._appointments = appointments
        self._locks = locks

    def execute(self, *, actor_id: Id, appointment_id: Id, text: str) -> Appointment:
        with self._uow:
            # Clinical notes are the clinician's alone; an admin is refused too.
            profile_id = clinician_profile(self._directory, actor_id)
            scope = ActorScope(ActorKind.CLINICIAN, actor_id, profile_id)
            current = locked_scoped_appointment(
                scope, self._appointments, self._locks, appointment_id
            )
            written = current.with_notes(text)
            self._appointments.save(written)
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor_id,
                    action="booking.appointment_notes_written",
                    entity_type="appointment",
                    entity_id=written.id,
                    at=self._clock.now(),
                    metadata={"fields": ("clinical_notes",)},
                )
            )
            return written
