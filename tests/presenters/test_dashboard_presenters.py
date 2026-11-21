from datetime import date

from drlibre.interfaces.web.presenters.dashboard import dashboard_view
from drlibre.reporting.domain.dashboard import (
    BusyClinician,
    Dashboard,
    DayCount,
    Range,
    Tally,
)
from drlibre.shared_kernel.ids import Id

DAYS = (date(2026, 11, 19), date(2026, 11, 20))


def dashboard(tally: Tally, *, available: int, counted: tuple[DayCount, ...] = ()) -> Dashboard:
    return Dashboard.from_figures(
        period=Range.WEEK,
        tally=tally,
        available_minutes=available,
        waitlist_size=2,
        days=DAYS,
        counted=counted,
        busiest=tuple(BusyClinician(Id(), f"Dr {n}", 9 - n) for n in range(7)),
    )


def tiles(view: object) -> dict[str, str]:
    return {t.label: t.value for t in view.tiles}  # type: ignore[attr-defined]


def test_without_activity_every_ratio_shows_not_available() -> None:
    """Story tableau de bord : un dénominateur nul affiche « n/a », jamais 0 %."""
    view = dashboard_view(dashboard(Tally(0, 0, 0, 0, 0), available=0))

    shown = tiles(view)
    assert [shown[k] for k in ("Utilisation", "Taux d'absence", "Part en ligne")] == ["n/a"] * 3
    assert (shown["RDV"], shown["Annulations"], shown["En liste d'attente"]) == ("0", "0", "2")


def test_each_ratio_shows_its_rounded_percentage() -> None:
    """Story tableau de bord : utilisation, absences et part en ligne en pourcentage entier."""
    view = dashboard_view(dashboard(Tally(8, 3, 1, 5, 90), available=360))

    shown = tiles(view)
    assert (shown["Utilisation"], shown["Taux d'absence"], shown["Part en ligne"]) == (
        "25 %",
        "13 %",
        "63 %",
    )


def test_bars_are_a_share_of_the_busiest_day_and_keep_the_count_as_text() -> None:
    """Story tableau de bord : une barre par jour proportionnelle au maximum, nombre en texte."""
    counted = (DayCount(DAYS[0], 1), DayCount(DAYS[1], 12))

    view = dashboard_view(dashboard(Tally(13, 0, 0, 0, 0), available=60, counted=counted))

    assert [(d.day, d.count, d.width) for d in view.days] == [
        ("jeu. 19/11", 1, 10),
        ("ven. 20/11", 12, 100),
    ]


def test_the_period_links_mark_the_current_one_and_the_top_keeps_five() -> None:
    """Story tableau de bord : période en lien, courante marquée ; top 5 des praticiens."""
    view = dashboard_view(dashboard(Tally(0, 0, 0, 0, 0), available=0))

    assert [(r.url, r.current) for r in view.ranges] == [
        ("/console/?range=today", False),
        ("/console/?range=7", True),
        ("/console/?range=30", False),
    ]
    assert [b.name for b in view.busiest] == ["Dr 0", "Dr 1", "Dr 2", "Dr 3", "Dr 4"]
