import os
from logging.config import dictConfig
from typing import Any

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("drlibre")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.conf.beat_schedule = {
    "heartbeat": {"task": "drlibre.heartbeat", "schedule": 60.0},
    "expire-booking-holds": {"task": "drlibre.expire_booking_holds", "schedule": 60.0},
    "expire-waitlist": {"task": "drlibre.expire_waitlist", "schedule": 60.0},
    "send-appointment-reminders": {
        "task": "drlibre.send_appointment_reminders",
        "schedule": crontab(minute="*/15"),
    },
    "extend-slot-horizon": {
        "task": "drlibre.extend_slot_horizon",
        "schedule": crontab(hour=0, minute=15),
    },
}
app.autodiscover_tasks(["drlibre.interfaces.jobs"])


@setup_logging.connect
def use_django_logging(**_: Any) -> None:
    from django.conf import settings

    dictConfig(settings.LOGGING)
