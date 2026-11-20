import threading
from types import TracebackType

from django.db import transaction
from django.db.transaction import Atomic

from drlibre.shared_kernel.unit_of_work import UnitOfWork


class DjangoUnitOfWork(UnitOfWork):
    def __init__(self) -> None:
        # The container is shared, so each thread keeps its own stack of open transactions.
        self._local = threading.local()

    def _stack(self) -> list[Atomic]:
        if not hasattr(self._local, "open"):
            self._local.open = []
        return self._local.open

    def __enter__(self) -> None:
        atomic = transaction.atomic()
        atomic.__enter__()
        self._stack().append(atomic)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._stack().pop().__exit__(exc_type, exc, tb)
