from collections.abc import Mapping

from drlibre.shared_kernel.errors import DomainError, ErrorCode


def _refusal(code: ErrorCode, message: str, paths: list[str]) -> DomainError:
    return DomainError(code, message, {"fields": [{"field": p, "message": message} for p in paths]})


def changes(
    current: Mapping[str, object],
    incoming: Mapping[str, object],
    *,
    writable: frozenset[str],
    reserved: frozenset[str] = frozenset(),
) -> frozenset[str]:
    """Writable paths an update changes; a reserved one is forbidden, others invalid_input."""
    changed = sorted(
        p for p in current.keys() | incoming.keys() if current.get(p) != incoming.get(p)
    )
    if denied := [p for p in changed if p in reserved]:
        raise _refusal(ErrorCode.FORBIDDEN, "Ce champ est réservé à un autre rôle.", denied)
    if fixed := [p for p in changed if p not in writable]:
        raise _refusal(ErrorCode.INVALID_INPUT, "Ce champ n'est pas modifiable.", fixed)
    return frozenset(changed)
