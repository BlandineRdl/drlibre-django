from typing import Protocol


class DatabaseProbe(Protocol):
    def is_up(self) -> bool:
        """Return True when the database answers a trivial query."""
        ...
