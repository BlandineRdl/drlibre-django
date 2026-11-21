import uuid

import structlog
from celery import shared_task

from drlibre.bootstrap.container import container

logger = structlog.get_logger(__name__)


@shared_task(name="drlibre.heartbeat")
def heartbeat() -> dict[str, str]:
    with structlog.contextvars.bound_contextvars(correlation_id=str(uuid.uuid4())):
        report = container().check_health.execute()
        logger.info("heartbeat", status=report.status.value, database=report.database.value)
    return {"status": report.status.value, "database": report.database.value}


@shared_task(name="drlibre.extend_slot_horizon")
def extend_slot_horizon() -> None:
    with structlog.contextvars.bound_contextvars(correlation_id=str(uuid.uuid4())):
        container().extend_slot_horizon.execute()
        logger.info("slot_horizon_extended")
