from drlibre.identity.application.ports.inbound import Role, StaffLookup
from drlibre.organisation.application.ports.outbound import Clinician, StaffDirectory
from drlibre.shared_kernel.ids import Id


class IdentityStaffDirectory(StaffDirectory):
    """Asks the identity context, through its inbound port, who is an active clinician."""

    def __init__(self, lookup: StaffLookup) -> None:
        self._lookup = lookup

    def active_clinician(self, user_id: Id) -> Clinician | None:
        member = self._lookup.staff_member(user_id)
        if member is None or not member.active or member.role is not Role.CLINICIAN:
            return None
        return Clinician(member.user_id, member.full_name)
