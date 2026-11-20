import structlog
from django.db import DatabaseError, connection

from drlibre.health.application.ports.outbound import DatabaseProbe

logger = structlog.get_logger(__name__)


class DjangoDatabaseProbe(DatabaseProbe):
    def is_up(self) -> bool:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return cursor.fetchone() == (1,)
        except DatabaseError as error:
            logger.warning("database_probe_failed", error_type=type(error).__name__)
            return False
