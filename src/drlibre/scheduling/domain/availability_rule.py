from dataclasses import dataclass
from datetime import date, time

from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import FieldErrors

MIN_STEP = 5
MAX_STEP = 240


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
