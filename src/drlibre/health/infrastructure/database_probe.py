import structlog
from django.db import DatabaseError, connection
from django.db.backends.base.base import BaseDatabaseWrapper

from drlibre.health.application.ports.outbound import DatabaseProbe

logger = structlog.get_logger(__name__)


class DjangoDatabaseProbe(DatabaseProbe):
    def __init__(self, database: BaseDatabaseWrapper = connection) -> None:
        self._database = database

    def is_up(self) -> bool:
        try:
            with self._database.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
        except DatabaseError as error:
            logger.warning("database_probe_failed", error_type=type(error).__name__)
            return False
