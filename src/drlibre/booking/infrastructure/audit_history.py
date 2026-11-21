from drlibre.audit.application.ports.inbound import AuditQueries
from drlibre.booking.application.ports.outbound import AppointmentHistory, HistoryEntry
from drlibre.shared_kernel.ids import Id


class AuditAppointmentHistory(AppointmentHistory):
    """Asks the audit context, through its inbound port, for one appointment's entries."""

    def __init__(self, queries: AuditQueries) -> None:
        self._queries = queries

    def entries_of(self, appointment_id: Id) -> tuple[HistoryEntry, ...]:
        found = self._queries.entries_for("appointment", appointment_id)
        return tuple(HistoryEntry(e.actor_id, e.action, e.at) for e in found)
