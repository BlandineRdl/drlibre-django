from types import TracebackType
from typing import Protocol


class UnitOfWork(Protocol):
    def __enter__(self) -> None:
        """Open one transaction; nested units join the outer one."""
        ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        """Commit on a clean exit, roll every write back when an exception escapes."""
        ...
