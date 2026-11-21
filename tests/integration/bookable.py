import dataclasses
import re
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import redis
from django.conf import settings

from drlibre.booking.infrastructure.outbox_notices import OutboxBookingNotices
from drlibre.bootstrap.container import Adapters, Container, real_adapters, wire
from drlibre.identity.infrastructure.rate_limiter import RedisRateLimiter
from drlibre.scheduling.application.ports.inbound import Slot
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import StoredScene, stored_scene
from tests.fakes.clock import FixedClock
from tests.fakes.email_outbox import RecordingEmailOutbox

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
# A Monday, 09:00 in Paris, more than 120 minutes after NOW.
SLOT_START = datetime(2026, 11, 23, 8, tzinfo=UTC)
VISITOR = {
    "full_name": "Ana Martin",
    "birth_date": "1990-05-17",
    "email": "ana.martin@example.org",
    "phone": "0612345678",
    "reason": "Douleur",
    "accepted_terms": True,
    "network": "203.0.113.7",
}


@dataclass
class Bookable:
    """The real adapters on PostgreSQL with a fixed clock and emails recorded, not queued."""

    scene: StoredScene
    outbox: RecordingEmailOutbox
    limiter: RedisRateLimiter

    def app(self, at: datetime = NOW) -> Container:
        return wire(self.at(at))

    def at(self, instant: datetime) -> Adapters:
        return recorded(instant, self.outbox, self.limiter)

    def visitor(self) -> dict[str, object]:
        # A fresh address per run, so the hourly limits of earlier runs never apply.
        return {**VISITOR, "email": f"visiteur.{uuid.uuid4().hex[:10]}@example.org"}

    @property
    def clinician(self) -> Id:
        return self.scene.clinicians[0].id

    def code(self) -> str:
        found = [m for m in self.outbox.queued if m.subject == "Votre code de vérification"]
        match = re.search(r"\d{6}", found[-1].body)
        assert match is not None
        return match.group()


def recorded(at: datetime, outbox: RecordingEmailOutbox, limiter: RedisRateLimiter) -> Adapters:
    adapters = real_adapters(FixedClock(at))
    booking = adapters.booking
    notices = OutboxBookingNotices(
        outbox=outbox,
        notify=adapters.notify,
        directory=booking.directory,
        patients=booking.patients,
        public_base_url="http://localhost:8000",
    )
    booking = dataclasses.replace(booking, notices=notices, limiter=limiter)
    return dataclasses.replace(adapters, booking=booking)


@contextmanager
def bookable(*, duration_minutes: int = 30) -> Generator[Bookable]:
    """Two clinicians publishing Monday 09:00 to 12:00 every 30 minutes, slots stored."""
    client = redis.Redis.from_url(settings.REDIS_URL)
    prefix = f"drlibre-test:{uuid.uuid4().hex}"
    limiter = RedisRateLimiter(client, prefix=prefix)
    scene = stored_scene(duration_minutes=duration_minutes)
    outbox = RecordingEmailOutbox()
    world = Bookable(scene, outbox, limiter)
    fields = {"weekday": "1", "start": "09:00", "end": "12:00", "step_minutes": "30"}
    for profile in scene.clinicians:
        world.app().save_availability_rule.execute(
            actor=profile.user_id, rule_id=None, fields=fields
        )
    try:
        yield world
    finally:
        for key in client.scan_iter(f"{prefix}:*"):
            client.delete(key)


def free_starts(app: Container, scene: StoredScene, clinician: Id | None) -> list[datetime]:
    slots: tuple[Slot, ...] = app.find_free_slots.execute(
        appointment_type_id=scene.kind,
        clinician_id=clinician,
        start=SLOT_START - timedelta(hours=1),
        end=SLOT_START + timedelta(hours=5),
    )
    return [s.start for s in slots]
