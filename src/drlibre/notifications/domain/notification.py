import dataclasses
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from zoneinfo import ZoneInfo

from drlibre.shared_kernel.ids import Id


class NotificationKind(StrEnum):
    SCHEDULE_CHANGED = "SCHEDULE_CHANGED"
    APPOINTMENT_CANCELLED = "APPOINTMENT_CANCELLED"
    APPOINTMENT_REMINDER = "APPOINTMENT_REMINDER"


class AppointmentEvent(StrEnum):
    BOOKED = "BOOKED"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"
    REMINDED = "REMINDED"


# Kind, title and body template of each event's notification.
_WORDING = {
    AppointmentEvent.BOOKED: (
        NotificationKind.SCHEDULE_CHANGED,
        "RDV réservé",
        "Votre RDV du {when} est réservé.",
    ),
    AppointmentEvent.RESCHEDULED: (
        NotificationKind.SCHEDULE_CHANGED,
        "RDV déplacé",
        "Votre RDV est déplacé au {when}.",
    ),
    AppointmentEvent.CANCELLED: (
        NotificationKind.APPOINTMENT_CANCELLED,
        "RDV annulé",
        "Votre RDV du {when} est annulé.",
    ),
    AppointmentEvent.REMINDED: (
        NotificationKind.APPOINTMENT_REMINDER,
        "Rappel de RDV",
        "Rappel : votre RDV a lieu le {when}.",
    ),
}


@dataclass(frozen=True, slots=True)
class Notification:
    id: Id
    recipient_id: Id
    kind: NotificationKind
    title: str
    body: str
    appointment_id: Id | None
    created_at: datetime
    read_at: datetime | None = None

    @classmethod
    def for_event(
        cls,
        *,
        event: AppointmentEvent,
        recipient_id: Id,
        appointment_id: Id,
        start: datetime,
        zone_name: str,
        at: datetime,
    ) -> "Notification":
        """Title and a body holding only the local time: no name, reason or email."""
        kind, title, template = _WORDING[event]
        local = start.astimezone(ZoneInfo(zone_name))
        body = template.format(when=f"{local:%d/%m/%Y à %H:%M} ({zone_name})")
        return cls(
            id=Id(),
            recipient_id=recipient_id,
            kind=kind,
            title=title,
            body=body,
            appointment_id=appointment_id,
            created_at=at,
        )

    @property
    def is_read(self) -> bool:
        return self.read_at is not None

    def mark_read(self, at: datetime) -> "Notification":
        """Read at the first time it is marked; later marks keep that time."""
        return self if self.is_read else dataclasses.replace(self, read_at=at)
