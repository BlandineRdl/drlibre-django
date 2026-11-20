import os
from collections.abc import Callable

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import structlog  # noqa: E402
from django.db import transaction  # noqa: E402

logger = structlog.get_logger("drlibre.seed")

# Each seeder upserts its rows, so the whole seed can run again safely.
SEEDERS: list[Callable[[], None]] = []


def main() -> None:
    with transaction.atomic():
        for seeder in SEEDERS:
            seeder()
    logger.info("seed_done", seeders=len(SEEDERS))


if __name__ == "__main__":
    main()
