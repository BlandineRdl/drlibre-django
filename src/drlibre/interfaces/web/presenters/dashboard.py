from dataclasses import dataclass

from drlibre.interfaces.web.presenters.console import NavLink
from drlibre.interfaces.web.presenters.slots import day_label
from drlibre.reporting.application.ports.inbound import Dashboard, Range, Ratio

DASHBOARD_URL = "/console/"
RANGE_LABELS = {Range.TODAY: "Aujourd'hui", Range.WEEK: "7 jours", Range.MONTH: "30 jours"}
NO_BUSIEST = "Aucun RDV sur la période"
# Bar widths are CSS classes in steps of this many percent: the CSP forbids inline styles.
BAR_STEP = 10


@dataclass(frozen=True, slots=True)
class Tile:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class DayBar:
    day: str
    count: int
    width: int


@dataclass(frozen=True, slots=True)
class BusyRow:
    name: str
    count: int


@dataclass(frozen=True, slots=True)
class DashboardView:
    range_label: str
    ranges: tuple[NavLink, ...]
    tiles: tuple[Tile, ...]
    days: tuple[DayBar, ...]
    busiest: tuple[BusyRow, ...]
    no_busiest: str


def ratio_text(ratio: Ratio) -> str:
    percent = ratio.percent
    return "n/a" if percent is None else f"{percent} %"


def bar_width(count: int, top: int) -> int:
    """Share of the busiest day, rounded up to the next step so any count shows."""
    if top == 0 or count == 0:
        return 0
    return -(-100 * count // (top * BAR_STEP)) * BAR_STEP


def dashboard_view(dashboard: Dashboard) -> DashboardView:
    top = max((d.count for d in dashboard.per_day), default=0)
    return DashboardView(
        range_label=RANGE_LABELS[dashboard.range],
        ranges=tuple(
            NavLink(f"{DASHBOARD_URL}?range={r.value}", label, r is dashboard.range)
            for r, label in RANGE_LABELS.items()
        ),
        tiles=(
            Tile("RDV", str(dashboard.appointments)),
            Tile("Annulations", str(dashboard.cancellations)),
            Tile("Utilisation", ratio_text(dashboard.utilisation)),
            Tile("Taux d'absence", ratio_text(dashboard.no_show_rate)),
            Tile("Part en ligne", ratio_text(dashboard.online_share)),
            Tile("En liste d'attente", str(dashboard.waitlist_size)),
        ),
        days=tuple(
            DayBar(day_label(d.day), d.count, bar_width(d.count, top)) for d in dashboard.per_day
        ),
        busiest=tuple(BusyRow(c.name, c.count) for c in dashboard.busiest),
        no_busiest=NO_BUSIEST,
    )
