from drlibre.identity.domain.user import Role
from drlibre.interop.application.ports.inbound import Reader, ReaderKind, Readers
from drlibre.shared_kernel.ids import Id
from tests.fakes.organisation import InMemoryClinicianProfiles
from tests.fakes.users import InMemoryUsers


class InMemoryReaders(Readers):
    def __init__(self, users: InMemoryUsers, profiles: InMemoryClinicianProfiles) -> None:
        self._users = users
        self._profiles = profiles

    def of(self, user_id: Id | None) -> Reader:
        if user_id is None:
            return Reader.anonymous()
        profile = self._profiles.for_user(user_id)
        if profile is not None:
            return Reader(ReaderKind.CLINICIAN, user_id, profile.id)
        user = self._users.get(user_id)
        if user is not None and user.role is Role.ADMIN and user.active:
            return Reader(ReaderKind.ADMIN, user_id)
        return Reader(ReaderKind.PATIENT, user_id)
