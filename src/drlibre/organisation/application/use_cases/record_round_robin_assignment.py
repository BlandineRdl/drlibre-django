import dataclasses
from datetime import datetime

from drlibre.organisation.application.ports.inbound import RecordRoundRobinAssignment
from drlibre.organisation.application.ports.outbound import ClinicianProfiles
from drlibre.shared_kernel.ids import Id


class RecordRoundRobinAssignmentUseCase(RecordRoundRobinAssignment):
    """No audit of its own: the booking that triggers it is audited in the same unit."""

    def __init__(self, *, profiles: ClinicianProfiles) -> None:
        self._profiles = profiles

    def execute(self, *, clinician_id: Id, at: datetime) -> None:
        profile = self._profiles.get(clinician_id)
        if profile is not None:
            self._profiles.save(dataclasses.replace(profile, last_assigned_at=at))
