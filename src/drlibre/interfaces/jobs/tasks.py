import smtplib
import uuid

import structlog
from celery import shared_task

from drlibre.bootstrap.container import container
from drlibre.notifications.application.email_task import REDACTED, SEND_EMAIL_TASK
from drlibre.notifications.application.ports.outbound import EmailMessage

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


@shared_task(
    name=SEND_EMAIL_TASK,
    autoretry_for=(smtplib.SMTPException, OSError),
    retry_backoff=True,
    max_retries=5,
    # A retry is a new message: keep the body out of its repr too.
    retry_kwargs={"argsrepr": REDACTED, "kwargsrepr": REDACTED},
)
def send_email(*, to: list[str], subject: str, body: str) -> None:
    container().mailer.send(EmailMessage(to=tuple(to), subject=subject, body=body))
    logger.info("email_sent", recipients=len(to))


@shared_task(name="drlibre.expire_booking_holds")
def expire_booking_holds() -> int:
    with structlog.contextvars.bound_contextvars(correlation_id=str(uuid.uuid4())):
        expired = container().expire_holds.execute()
        logger.info("booking_holds_expired", count=expired)
    return expired
