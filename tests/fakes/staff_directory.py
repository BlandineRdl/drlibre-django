from drlibre.organisation.application.ports.outbound import Clinician, StaffDirectory
from drlibre.shared_kernel.ids import Id


class InMemoryStaffDirectory(StaffDirectory):
    def __init__(self) -> None:
        self.active_clinicians: dict[Id, Clinician] = {}

    def active_clinician(self, user_id: Id) -> Clinician | None:
        return self.active_clinicians.get(user_id)
