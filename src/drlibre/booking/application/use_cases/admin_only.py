from drlibre.booking.application.ports.outbound import Staff
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

ADMINS_ONLY = "Réservé aux administrateurs."


def refuse_non_admin(staff: Staff, actor_id: Id) -> None:
    if not staff.is_admin(actor_id):
        raise DomainError(ErrorCode.FORBIDDEN, ADMINS_ONLY)
