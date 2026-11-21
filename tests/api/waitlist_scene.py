from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta

from django.conf import settings
from django.test import Client

from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.domain.waitlist import WaitlistEntry
from drlibre.booking.infrastructure.repositories import DjangoWaitlist
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role, User
from tests.builders import stored_session, stored_user
from tests.integration.bookable import NOW, SLOT_START, Bookable, bookable


@dataclass
class Waiting:
    """A passwordless patient waiting for the type of a cancelled Monday 09:00 Paris slot."""

    world: Bookable
    patient: User
    entry: WaitlistEntry
    freed: Appointment

    def client(self, user: User | None = None) -> Client:
        client = Client()
        client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(user or self.patient)
        return client

    def stored(self) -> WaitlistEntry:
        found = DjangoWaitlist().get(self.entry.id)
        assert found is not None
        return found


@contextmanager
def waitlist_scene(*, offered: bool = True) -> Generator[Waiting]:
    """Offered: the entry joined before the cancel; else after it, still WAITING."""
    with bookable() as world:
        app = world.app()
        use_container(app)
        leaving = stored_user(Role.PATIENT, password=None)
        freed = app.book_appointment.execute(
            patient_id=leaving.id,
            appointment_type_id=world.scene.kind,
            clinician_id=world.clinician,
            start=SLOT_START,
        )
        patient = stored_user(Role.PATIENT, password=None)
        entry = WaitlistEntry.join(
            patient_id=patient.id,
            appointment_type_id=world.scene.kind,
            clinician_id=None,
            earliest=SLOT_START - timedelta(days=1),
            latest=SLOT_START + timedelta(days=1),
            at=NOW,
        )

        def cancel() -> None:
            app.cancel_appointment.execute(
                appointment_id=freed.id, patient_id=leaving.id, reason="Empêchement"
            )

        if offered:
            DjangoWaitlist().add(entry)
            cancel()
        else:
            cancel()
            DjangoWaitlist().add(entry)
        try:
            yield Waiting(world, patient, entry, freed)
        finally:
            use_container(None)
