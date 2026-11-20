from dataclasses import dataclass

from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class Dependent:
    kind: str
    id: Id
    label: str


@dataclass(frozen=True, slots=True)
class Dependents:
    items: tuple[Dependent, ...] = ()

    @classmethod
    def of(cls, *groups: tuple[Dependent, ...]) -> "Dependents":
        return cls(tuple(item for group in groups for item in group))

    def refuse_if_any(self, message: str) -> None:
        """Raise has_dependents listing kind, id and label of each record still in use."""
        if self.items:
            listed = [{"kind": d.kind, "id": str(d.id), "label": d.label} for d in self.items]
            raise DomainError(ErrorCode.HAS_DEPENDENTS, message, {"dependents": listed})
