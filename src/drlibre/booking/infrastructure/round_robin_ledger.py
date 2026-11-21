from datetime import datetime

from drlibre.booking.application.ports.outbound import RoundRobinLedger
from drlibre.organisation.application.ports.inbound import RecordRoundRobinAssignment
from drlibre.shared_kernel.ids import Id


class OrganisationRoundRobinLedger(RoundRobinLedger):
    """Hands the assignment to organisation, in the caller's unit of work."""

    def __init__(self, record: RecordRoundRobinAssignment) -> None:
        self._record = record

    def record(self, clinician_id: Id, at: datetime) -> None:
        self._record.execute(clinician_id=clinician_id, at=at)
