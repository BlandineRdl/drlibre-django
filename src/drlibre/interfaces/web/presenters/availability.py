import colorsys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from drlibre.scheduling.application.ports.inbound import WEEKDAYS, AvailabilityRule, TimeOff
from drlibre.shared_kernel.ids import Id

RULES_URL = "/workspace/availability/"
TIME_OFF_URL = "/workspace/time-off/"
# Weekdays numbered 0 Sunday to 6 Saturday (spec 3.1), shown Monday first.
WEEK_ORDER = (1, 2, 3, 4, 5, 6, 0)
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


# Palette classes `.hue-0` to `.hue-7` in drlibre.css, red to pink around the wheel.
HUES = 8


@dataclass(frozen=True, slots=True)
class CellView:
    text: str
    kind: str
    colour: str = ""
    url: str = ""

    @property
    def hue_class(self) -> str:
        """The palette class nearest the type colour: the CSP forbids inline styles."""
        if len(self.colour) != 7:
            return ""
        red, green, blue = (int(self.colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
        hue, _, saturation = colorsys.rgb_to_hls(red, green, blue)
        return "" if saturation < 0.15 else f"hue-{round(hue * HUES) % HUES}"


@dataclass(frozen=True, slots=True)
class GridAppointment:
    """An appointment placed on the week grid, named by its type."""

    start: datetime
    end: datetime
    label: str
    colour: str
    url: str


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


WEEK_MARGIN = timedelta(days=14)


def week_start(raw: str | None, *, today: date) -> date:
    """Monday of the week holding ?week=YYYY-MM-DD; a missing or bad value means this week."""
    try:
        day = date.fromisoformat(raw or "")
    except ValueError:
        day = today
    # The grid and its previous and next links need two weeks on either side.
    if not date.min + WEEK_MARGIN <= day <= date.max - WEEK_MARGIN:
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
    appointments: tuple[GridAppointment, ...] = (),
    title: str = "",
) -> WeekView:
    """Read-only 07:00-19:00 grid in 30-minute rows, each cell labelled in text."""
    tz = ZoneInfo(time_zone)
    days = tuple(monday + timedelta(days=n) for n in range(7))
    rows = []
    for n in range(GRID_ROWS):
        start = datetime.combine(monday, GRID_START) + n * GRID_STEP
        cells = tuple(
            _cell(day, start.time(), (start + GRID_STEP).time(), tz, rules, time_offs, appointments)
            for day in days
        )
        rows.append(GridRowView(f"{start:%H:%M}", cells))
    return WeekView(
        title=title or f"Calendrier de {clinician}",
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
    appointments: tuple[GridAppointment, ...],
) -> CellView:
    since = datetime.combine(day, start, tzinfo=tz)
    until = datetime.combine(day, end, tzinfo=tz)
    booked = next((a for a in appointments if a.start < until and since < a.end), None)
    if booked is not None:
        return CellView(booked.label, "appointment", booked.colour, booked.url)
    if any(t.start < until and since < t.end for t in time_offs):
        return CellView(TIME_OFF, "time-off")
    if any(r.applies_on(day) and r.start < end and start < r.end for r in rules):
        return CellView(AVAILABLE, "available")
    return CellView("", "")
