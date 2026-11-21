import re
from datetime import UTC, datetime

from drlibre.booking.application.ports.inbound import Appointment

CRLF = "\r\n"
FOLD_AT = 75
# RFC 5545 TEXT escapes backslash, semicolon and comma with a backslash.
_TEXT_SPECIALS = re.compile(r"([\\;,])")


def _stamp(instant: datetime) -> str:
    return instant.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _escape(text: str) -> str:
    escaped = _TEXT_SPECIALS.sub(r"\\\1", text)
    return escaped.replace("\r", "").replace("\n", "\\n")


def _fold(line: str) -> str:
    """Wrap a content line at 75 octets, each continuation starting with one space."""
    parts: list[str] = []
    current = ""
    for char in line:
        limit = FOLD_AT if not parts else FOLD_AT - 1
        if len((current + char).encode()) > limit:
            parts.append(current)
            current = char
        else:
            current += char
    parts.append(current)
    return (CRLF + " ").join(parts)


def calendar_file(
    appointment: Appointment, *, summary: str, location: str, stamped_at: datetime
) -> str:
    """The appointment as an RFC 5545 calendar: UTC times, CRLF line ends, no reason."""
    lines = (
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//DrLibre//Rendez-vous//FR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:{appointment.id}@drlibre",
        f"DTSTAMP:{_stamp(stamped_at)}",
        f"DTSTART:{_stamp(appointment.start)}",
        f"DTEND:{_stamp(appointment.end)}",
        f"SUMMARY:{_escape(summary)}",
        f"LOCATION:{_escape(location)}",
        "END:VEVENT",
        "END:VCALENDAR",
    )
    return CRLF.join(_fold(line) for line in lines) + CRLF
