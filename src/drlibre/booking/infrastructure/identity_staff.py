from drlibre.booking.application.ports.outbound import Staff
from drlibre.identity.application.ports.inbound import Role, StaffLookup
from drlibre.shared_kernel.ids import Id


class IdentityStaff(Staff):
    """Reads staff roles through identity's StaffLookup."""

    def __init__(self, lookup: StaffLookup) -> None:
        self._lookup = lookup

    def is_admin(self, user_id: Id) -> bool:
        member = self._lookup.staff_member(user_id)
        return member is not None and member.active and member.role is Role.ADMIN
