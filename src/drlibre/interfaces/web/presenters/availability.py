from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.interfaces.web.presenters.forms import Choice, FieldSpec
from drlibre.scheduling.application.ports.inbound import AvailabilityRule, TimeOff
from drlibre.shared_kernel.ids import Id

RULES_URL = "/workspace/availability/"
TIME_OFF_URL = "/workspace/time-off/"
# Weekdays numbered 0 Sunday to 6 Saturday (spec 3.1), shown Monday first.
WEEKDAYS = ("Dimanche", "Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi")
WEEK_ORDER = (1, 2, 3, 4, 5, 6, 0)
WEEKDAY_CHOICES = tuple(Choice(str(day), WEEKDAYS[day]) for day in WEEK_ORDER)
GRID_START = time(7)
GRID_ROWS = 24
GRID_STEP = timedelta(minutes=30)
AVAILABLE = "Disponible"
TIME_OFF = "Absence"
_DONE = {
    "created": "L'élément a été créé.",
    "updated": "Les modifications ont été enregistrées.",
    "deleted": "L'élément a été supprimé.",
}


def _hours(rule: AvailabilityRule) -> str:
    return f"{rule.start:%H:%M}-{rule.end:%H:%M}"


def local_text(instant: datetime, time_zone: str) -> str:
    return f"{instant.astimezone(ZoneInfo(time_zone)):%d/%m/%Y %H:%M}"


def weekly_summary(rules: tuple[AvailabilityRule, ...]) -> str:
    """Weekday then local HH:MM-HH:MM ranges, Monday first."""
    days = []
    for day in WEEK_ORDER:
        ranges = sorted(_hours(r) for r in rules if r.weekday == day)
        if ranges:
            days.append(f"{WEEKDAYS[day][:3]} {', '.join(ranges)}")
    return " · ".join(days) or "Aucune plage"


@dataclass(frozen=True, slots=True)
class RuleRowView:
    label: str
    day: str
    hours: str
    step: str
    room: str
    edit_url: str
    delete_url: str


@dataclass(frozen=True, slots=True)
class RulesView:
    time_zone: str
    rows: tuple[RuleRowView, ...]
    status: str


def rules_view(
    rules: tuple[AvailabilityRule, ...],
    *,
    time_zone: str,
    room_labels: Mapping[Id, str],
    done: str | None = None,
) -> RulesView:
    ordered = sorted(rules, key=lambda r: (WEEK_ORDER.index(r.weekday), r.start))
    rows = tuple(
        RuleRowView(
            label=r.label,
            day=WEEKDAYS[r.weekday],
            hours=_hours(r),
            step=f"{r.step_minutes} min",
            room=room_labels.get(r.room_id, "") if r.room_id else "Aucune",
            edit_url=f"{RULES_URL}{r.id}/edit",
            delete_url=f"{RULES_URL}{r.id}/delete",
        )
        for r in ordered
    )
    return RulesView(time_zone=time_zone, rows=rows, status=_DONE.get(done or "", ""))


@dataclass(frozen=True, slots=True)
class TimeOffRowView:
    label: str
    start: str
    end: str
    reason: str
    delete_url: str


@dataclass(frozen=True, slots=True)
class TimeOffsView:
    time_zone: str
    rows: tuple[TimeOffRowView, ...]
    status: str


def time_off_label(time_off: TimeOff, time_zone: str) -> str:
    return f"{local_text(time_off.start, time_zone)} → {local_text(time_off.end, time_zone)}"


def time_offs_view(
    time_offs: tuple[TimeOff, ...], *, time_zone: str, done: str | None = None
) -> TimeOffsView:
    rows = tuple(
        TimeOffRowView(
            label=time_off_label(t, time_zone),
            start=local_text(t.start, time_zone),
            end=local_text(t.end, time_zone),
            reason=t.reason,
            delete_url=f"{TIME_OFF_URL}{t.id}/delete",
        )
        for t in time_offs
    )
    return TimeOffsView(time_zone=time_zone, rows=rows, status=_DONE.get(done or "", ""))


def rule_fields(time_zone: str) -> tuple[FieldSpec, ...]:
    local = f"HH:MM, heure locale ({time_zone})."
    return (
        FieldSpec("weekday", "Jour", kind="select"),
        FieldSpec("start", "Début", kind="time", help=local),
        FieldSpec("end", "Fin", kind="time", help=f"Après le début ; {local}"),
        FieldSpec("step_minutes", "Pas en minutes", kind="number", help="De 5 à 240 minutes."),
        FieldSpec(
            "room_id",
            "Salle",
            kind="select",
            required=False,
            help="Une salle active de votre département.",
        ),
    )


def time_off_fields(time_zone: str) -> tuple[FieldSpec, ...]:
    local = f"Date et heure locales ({time_zone})."
    return (
        FieldSpec("start", "Début", kind="datetime-local", help=local),
        FieldSpec("end", "Fin", kind="datetime-local", help=f"Après le début ; {local}"),
        FieldSpec(
            "reason", "Motif", kind="textarea", required=False, help="200 caractères au plus."
        ),
    )


def rule_values(rule: AvailabilityRule) -> dict[str, str]:
    """A stored rule as the raw text its edit form starts from."""
    return {
        "weekday": str(rule.weekday),
        "start": f"{rule.start:%H:%M}",
        "end": f"{rule.end:%H:%M}",
        "step_minutes": str(rule.step_minutes),
        "room_id": str(rule.room_id) if rule.room_id else "",
    }


@dataclass(frozen=True, slots=True)
class DayView:
    short: str
    long: str


@dataclass(frozen=True, slots=True)
class CellView:
    text: str
    kind: str


@dataclass(frozen=True, slots=True)
class GridRowView:
    time: str
    cells: tuple[CellView, ...]


@dataclass(frozen=True, slots=True)
class WeekView:
    title: str
    time_zone: str
    week_label: str
    days: tuple[DayView, ...]
    rows: tuple[GridRowView, ...]
    previous_url: str
    this_url: str
    next_url: str


def week_start(raw: str | None, *, today: date) -> date:
    """Monday of the week holding ?week=YYYY-MM-DD; a missing or bad value means this week."""
    try:
        day = date.fromisoformat(raw or "")
    except ValueError:
        day = today
    return day - timedelta(days=day.weekday())


def week_view(
    *,
    clinician: str,
    time_zone: str,
    monday: date,
    rules: tuple[AvailabilityRule, ...],
    time_offs: tuple[TimeOff, ...],
    base_url: str,
) -> WeekView:
    """Read-only 07:00-19:00 grid in 30-minute rows, each cell labelled in text."""
    tz = ZoneInfo(time_zone)
    days = tuple(monday + timedelta(days=n) for n in range(7))
    rows = []
    for n in range(GRID_ROWS):
        start = datetime.combine(monday, GRID_START) + n * GRID_STEP
        cells = tuple(
            _cell(day, start.time(), (start + GRID_STEP).time(), tz, rules, time_offs)
            for day in days
        )
        rows.append(GridRowView(f"{start:%H:%M}", cells))
    return WeekView(
        title=f"Calendrier de {clinician}",
        time_zone=time_zone,
        week_label=f"Semaine du {monday:%d/%m/%Y}",
        days=tuple(_day(d) for d in days),
        rows=tuple(rows),
        previous_url=f"{base_url}?week={monday - timedelta(days=7)}",
        this_url=base_url,
        next_url=f"{base_url}?week={monday + timedelta(days=7)}",
    )


def _day(day: date) -> DayView:
    name = WEEKDAYS[day.isoweekday() % 7]
    return DayView(f"{name[:3]} {day:%d/%m}", f"{name} {day:%d/%m/%Y}")


def _cell(
    day: date,
    start: time,
    end: time,
    tz: ZoneInfo,
    rules: tuple[AvailabilityRule, ...],
    time_offs: tuple[TimeOff, ...],
) -> CellView:
    since = datetime.combine(day, start, tzinfo=tz)
    until = datetime.combine(day, end, tzinfo=tz)
    if any(t.start < until and since < t.end for t in time_offs):
        return CellView(TIME_OFF, "time-off")
    if any(r.applies_on(day) and r.start < end and start < r.end for r in rules):
        return CellView(AVAILABLE, "available")
    return CellView("", "")
