import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, time

from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import FieldErrors, parse_id

MIN_STEP = 5
MAX_STEP = 240
WEEKDAYS = ("Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi")
_HHMM = re.compile(r"([01]\d|2[0-3]):[0-5]\d")


def weekday_of(day: date) -> int:
    """Weekday numbered 0 Sunday to 6 Saturday, as spec 3.1 states."""
    return day.isoweekday() % 7


@dataclass(frozen=True, slots=True)
class AvailabilityRule:
    """A weekly window of one clinician, in the hospital's local wall-clock time."""

    id: Id
    clinician_id: Id
    weekday: int
    start: time
    end: time
    step_minutes: int
    room_id: Id | None
    valid_from: date
    valid_to: date | None

    @classmethod
    def from_form(
        cls,
        raw: Mapping[str, str],
        *,
        id: Id,
        clinician_id: Id,
        valid_from: date,
        valid_to: date | None,
    ) -> "AvailabilityRule":
        f = FieldErrors()
        weekday = f.integer("weekday", raw.get("weekday", ""), minimum=0)
        start = _clock_time(f, "start", raw.get("start", ""))
        end = _clock_time(f, "end", raw.get("end", ""))
        step = f.integer("step_minutes", raw.get("step_minutes", ""), minimum=MIN_STEP)
        room_raw = raw.get("room_id", "").strip()
        room_id = parse_id(room_raw) if room_raw else None
        if room_raw and room_id is None:
            f.add("room_id", "Choisissez une salle active de votre département.")
        f.raise_if_any()
        return cls(id, clinician_id, weekday, start, end, step, room_id, valid_from, valid_to)

    def __post_init__(self) -> None:
        f = FieldErrors()
        if not 0 <= self.weekday <= 6:
            f.add("weekday", "Choisissez un jour de la semaine.")
        for name, value in (("start", self.start), ("end", self.end)):
            if value.second or value.microsecond or value.tzinfo is not None:
                f.add(name, "Saisissez une heure au format HH:MM.")
        if self.end <= self.start:
            f.add("end", "L'heure de fin doit suivre l'heure de début.")
        if not MIN_STEP <= self.step_minutes <= MAX_STEP:
            f.add("step_minutes", f"Saisissez un pas entre {MIN_STEP} et {MAX_STEP} minutes.")
        if self.valid_to is not None and self.valid_to < self.valid_from:
            f.add("valid_to", "La date de fin de validité doit suivre la date de début.")
        f.raise_if_any()

    def applies_on(self, day: date) -> bool:
        return (
            weekday_of(day) == self.weekday
            and self.valid_from <= day
            and (self.valid_to is None or day <= self.valid_to)
        )

    @property
    def label(self) -> str:
        return f"{WEEKDAYS[self.weekday]} {self.start:%H:%M}-{self.end:%H:%M}"

    def clashes_with(self, other: "AvailabilityRule") -> bool:
        """Same weekday, overlapping hours and validity; touching rules do not clash."""
        return (
            other.id != self.id
            and other.weekday == self.weekday
            and self.start < other.end
            and other.start < self.end
            and (self.valid_to is None or other.valid_from <= self.valid_to)
            and (other.valid_to is None or self.valid_from <= other.valid_to)
        )


def _clock_time(f: FieldErrors, field: str, raw: str) -> time:
    value = raw.strip()
    if not _HHMM.fullmatch(value):
        f.add(field, "Saisissez une heure au format HH:MM.")
        return time()
    return time.fromisoformat(value)
