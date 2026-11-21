from django.http import HttpRequest

from drlibre.bootstrap.container import container
from drlibre.identity.application.ports.inbound import Identity
from drlibre.interfaces.web.auth import identity_of
from drlibre.interop.application.ports.inbound import Reader
from drlibre.shared_kernel.errors import DomainError, ErrorCode

REFUSED_BEARER = "Jeton invalide ou expiré."
BEARER_REQUIRED = "Un jeton bearer est requis."
FORCED_CHANGE_FIRST = "Changez d'abord votre mot de passe."


def gate(request: HttpRequest) -> bool:
    """Every FHIR call: a presented credential must be valid, its user free of a forced change."""
    identity = identity_of(request)
    if request.headers.get("Authorization") and identity is None:
        raise DomainError(ErrorCode.UNAUTHENTICATED, REFUSED_BEARER)
    if identity is not None and identity.must_change_password:
        raise DomainError(ErrorCode.FORBIDDEN, FORCED_CHANGE_FIRST)
    return True


def caller(request: HttpRequest) -> Identity:
    """The token holder of an interaction that needs one, such as every write."""
    identity = identity_of(request)
    if identity is None:
        raise DomainError(ErrorCode.UNAUTHENTICATED, BEARER_REQUIRED)
    return identity


def reader(request: HttpRequest) -> Reader:
    identity = identity_of(request)
    return container().readers.of(identity.user_id if identity else None)
