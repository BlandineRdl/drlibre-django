import threading
import time
from collections.abc import Callable

from django.db import connection, connections

from drlibre.shared_kernel.errors import DomainError

FIRST = "first"


class Race:
    """Holds the first writer after its read until the second writer waits on the lock."""

    def __init__(self) -> None:
        self.first_has_read = threading.Event()
        self.second_was_blocked: list[bool] = []

    def hold_first(self) -> None:
        # The slot refresh reads again, so only the overlap check holds.
        if threading.current_thread().name != FIRST or self.first_has_read.is_set():
            return
        self.first_has_read.set()
        self.second_was_blocked.append(_another_session_waits_on_a_lock())

    def run(self, first: Callable[[], object], second: Callable[[], object]) -> list[str]:
        outcomes: list[str] = []

        def write(action: Callable[[], object]) -> None:
            try:
                action()
                outcomes.append("saved")
            except DomainError as error:
                outcomes.append(error.code)
            finally:
                connections.close_all()

        threads = [
            threading.Thread(target=write, args=(first,), name=FIRST),
            threading.Thread(target=write, args=(second,)),
        ]
        threads[0].start()
        assert self.first_has_read.wait(5)
        threads[1].start()
        for thread in threads:
            thread.join(15)
        return sorted(outcomes)


def _another_session_waits_on_a_lock() -> bool:
    deadline = time.monotonic() + 5
    with connection.cursor() as cursor:
        while time.monotonic() < deadline:
            # Activity stats are a snapshot frozen for the transaction unless cleared.
            cursor.execute("SELECT pg_stat_clear_snapshot()")
            cursor.execute(
                "SELECT EXISTS (SELECT 1 FROM pg_stat_activity WHERE datname = current_database()"
                " AND wait_event_type = 'Lock' AND pid <> pg_backend_pid())"
            )
            row = cursor.fetchone()
            if row and row[0]:
                return True
            time.sleep(0.05)
    return False
