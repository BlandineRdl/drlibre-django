import copy
from types import TracebackType

from drlibre.shared_kernel.unit_of_work import UnitOfWork


class InMemoryUnitOfWork(UnitOfWork):
    """Snapshots the state of the fakes it guards and restores it when the unit fails."""

    def __init__(self, *stores: object) -> None:
        self.stores = list(stores)
        self.committed = 0
        self.rolled_back = 0
        self._snapshots: list[list[dict[str, object]]] = []

    def guard(self, *stores: object) -> None:
        self.stores.extend(stores)

    def __enter__(self) -> None:
        self._snapshots.append([copy.deepcopy(vars(store)) for store in self.stores])

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        snapshot = self._snapshots.pop()
        if exc_type is None:
            self.committed += 1
            return
        self.rolled_back += 1
        for store, saved in zip(self.stores, snapshot, strict=True):
            vars(store).clear()
            vars(store).update(saved)
