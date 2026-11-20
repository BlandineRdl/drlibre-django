from drlibre.identity.application.ports.outbound import StaffProfiles
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


class InMemoryStaffProfiles(StaffProfiles):
    def __init__(self) -> None:
        self.profiles: dict[Id, Dependent] = {}

    def profile_of(self, user_id: Id) -> Dependent | None:
        return self.profiles.get(user_id)
