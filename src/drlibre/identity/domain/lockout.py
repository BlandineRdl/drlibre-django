from datetime import timedelta

LOCKOUT_FAILURES = 10
LOCKOUT_WINDOW = timedelta(minutes=15)


def is_locked(*, failures: int) -> bool:
    return failures >= LOCKOUT_FAILURES
