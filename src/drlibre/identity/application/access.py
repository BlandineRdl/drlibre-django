from drlibre.identity.application.ports.inbound import Identity
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


def authorize_owned[T](record: T | None, owner_id: Id | None, identity: Identity) -> T:
    """Absent → not_found; another user's record → forbidden; admins reach every record."""
    if record is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Élément introuvable.")
    if identity.role is not Role.ADMIN and owner_id != identity.user_id:
        raise DomainError(ErrorCode.FORBIDDEN, "Cet élément appartient à un autre utilisateur.")
    return record
