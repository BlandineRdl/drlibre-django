from datetime import date, datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from drlibre.shared_kernel.ids import Id

BOOKING_URL = "/booking/new"
NO_AVAILABILITY = "Aucune disponibilité dans les 90 prochains jours"
DAYS = ("lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim.")


def local(instant: datetime, time_zone: str) -> datetime:
    return instant.astimezone(ZoneInfo(time_zone))


def day_label(day: date) -> str:
    return f"{DAYS[day.weekday()]} {day:%d/%m}"


def slot_label(instant: datetime, time_zone: str) -> str:
    at = local(instant, time_zone)
    return f"{day_label(at.date())} {at:%H:%M}"


def slot_instant(instant: datetime) -> str:
    return instant.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%SZ")


def clinician_booking_url(type_id: Id, clinician_id: Id, start: datetime) -> str:
    query = {"type": str(type_id), "clinician": str(clinician_id), "start": slot_instant(start)}
    return f"{BOOKING_URL}?{urlencode(query, safe=':')}"


def first_available_url(type_id: Id, department_id: Id, start: datetime) -> str:
    query = {"type": str(type_id), "department": str(department_id), "start": slot_instant(start)}
    return f"{BOOKING_URL}?{urlencode(query, safe=':')}"
