from drlibre.booking.application.ports.outbound import AppointmentHistory, HistoryEntry
from drlibre.shared_kernel.ids import Id
from tests.fakes.audit_log import InMemoryAuditLog


class InMemoryAppointmentHistory(AppointmentHistory):
    def __init__(self, log: InMemoryAuditLog) -> None:
        self.log = log

    def entries_of(self, appointment_id: Id) -> tuple[HistoryEntry, ...]:
        found = (
            e
            for e in self.log.entries
            if e.entity_type == "appointment" and e.entity_id == appointment_id
        )
        return tuple(
            HistoryEntry(e.actor, e.action, e.at) for e in sorted(found, key=lambda e: e.at)
        )
