from datetime import UTC, date, datetime, time

import pytest

from drlibre.reporting.domain.available_minutes import Absence
from drlibre.reporting.domain.dashboard import BUSIEST_COUNT, DayCount, Range, Tally
from tests.builders_reporting import ActivityScene, fake_activity, real_activity

REAL = [pytest.mark.integration, pytest.mark.django_db]
NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="sql", marks=REAL)]
)
def scene(request: pytest.FixtureRequest) -> ActivityScene:
    return fake_activity() if request.param == "fake" else real_activity()


def test_the_tally_counts_each_figure_of_the_range(scene: ActivityScene) -> None:
    """Spec 13: appointments, cancellations, no-shows, online share and active minutes."""
    dr = scene.clinician("Dr Paris", "Europe/Paris", True)
    scene.appointment(dr, datetime(2026, 11, 20, 9), 30, "BOOKED", "ONLINE")
    scene.appointment(dr, datetime(2026, 11, 19, 9), 45, "COMPLETED", "ROUND_ROBIN")
    scene.appointment(dr, datetime(2026, 11, 18, 9), 30, "CHECKED_IN", "STAFF")
    scene.appointment(dr, datetime(2026, 11, 17, 9), 30, "NO_SHOW", "ONLINE")
    scene.appointment(dr, datetime(2026, 11, 16, 9), 30, "CANCELLED", "ONLINE")
    scene.appointment(dr, datetime(2026, 11, 13, 9), 30, "BOOKED", "ONLINE")

    assert scene.queries.activity(NOW, Range.WEEK, BUSIEST_COUNT).tally == Tally(
        appointments=4, cancellations=1, no_shows=1, online=3, active_minutes=105
    )
    assert scene.queries.activity(NOW, Range.TODAY, BUSIEST_COUNT).tally == Tally(1, 0, 0, 1, 30)


def test_active_minutes_leave_out_a_deactivated_clinician_whose_appointments_still_count(
    scene: ActivityScene,
) -> None:
    """Règle §13 : l'utilisation ne compte que les RDV des praticiens actifs."""
    dr = scene.clinician("Dr Paris", "Europe/Paris", True)
    gone = scene.clinician("Dr Parti", "Europe/Paris", False)
    scene.appointment(dr, datetime(2026, 11, 20, 9), 30, "BOOKED", "ONLINE")
    scene.appointment(gone, datetime(2026, 11, 20, 9), 60, "COMPLETED", "STAFF")

    assert scene.queries.activity(NOW, Range.TODAY, BUSIEST_COUNT).tally == Tally(2, 0, 0, 1, 30)


def test_a_day_is_the_local_day_of_the_clinician_hospital(scene: ActivityScene) -> None:
    """Story indicateurs : jour compté dans le fuseau de l'hôpital du RDV."""
    late = datetime(2026, 11, 21, 1, tzinfo=UTC)
    cayenne = scene.clinician("Dr Cayenne", "America/Cayenne", True)
    paris = scene.clinician("Dr Paris", "Europe/Paris", True)
    scene.appointment(cayenne, datetime(2026, 11, 20, 23, 30), 30, "BOOKED", "ONLINE")
    scene.appointment(paris, datetime(2026, 11, 20, 23, 30), 30, "BOOKED", "ONLINE")

    assert scene.queries.activity(late, Range.TODAY, BUSIEST_COUNT).tally.appointments == 1
    assert scene.queries.activity(late, Range.WEEK, BUSIEST_COUNT).per_day == (
        DayCount(date(2026, 11, 20), 2),
    )


def test_days_list_not_cancelled_appointments_oldest_first(scene: ActivityScene) -> None:
    """Story jours : un compte par jour de RDV non annulés."""
    dr = scene.clinician("Dr Paris", "Europe/Paris", True)
    scene.appointment(dr, datetime(2026, 11, 20, 9), 30, "BOOKED", "ONLINE")
    scene.appointment(dr, datetime(2026, 11, 18, 9), 30, "NO_SHOW", "ONLINE")
    scene.appointment(dr, datetime(2026, 11, 18, 10), 30, "BOOKED", "ONLINE")
    scene.appointment(dr, datetime(2026, 11, 17, 9), 30, "CANCELLED", "ONLINE")

    assert scene.queries.activity(NOW, Range.WEEK, BUSIEST_COUNT).per_day == (
        DayCount(date(2026, 11, 18), 2),
        DayCount(date(2026, 11, 20), 1),
    )


def test_the_busiest_clinicians_rank_by_count_then_name(scene: ActivityScene) -> None:
    """Story praticiens chargés : nombre de RDV non annulés décroissant, égalité par nom."""
    b = scene.clinician("Dr B", "Europe/Paris", True)
    a = scene.clinician("Dr A", "Europe/Paris", True)
    c = scene.clinician("Dr C", "Europe/Paris", True)
    for clinician in (a, b):
        scene.appointment(clinician, datetime(2026, 11, 20, 9), 30, "BOOKED", "ONLINE")
    scene.appointment(c, datetime(2026, 11, 20, 9), 30, "BOOKED", "ONLINE")
    scene.appointment(c, datetime(2026, 11, 19, 9), 30, "COMPLETED", "ONLINE")
    scene.appointment(b, datetime(2026, 11, 19, 9), 30, "CANCELLED", "ONLINE")

    ranked = scene.queries.activity(NOW, Range.WEEK, 2).busiest

    assert [(r.clinician_id, r.name, r.count) for r in ranked] == [(c, "Dr C", 2), (a, "Dr A", 1)]


def test_the_waitlist_counts_waiting_and_offered_entries(scene: ActivityScene) -> None:
    """Spec 13: entries WAITING or OFFERED, whatever the range."""
    scene.clinician("Dr Paris", "Europe/Paris", True)
    for status in ("WAITING", "OFFERED", "BOOKED", "EXPIRED", "WAITING"):
        scene.waitlist(status)

    assert scene.queries.waitlist_size() == 3


def test_schedules_cover_active_clinicians_and_time_off_in_the_window(
    scene: ActivityScene,
) -> None:
    """Spec 13: rule hours of active clinicians minus their time off."""
    cayenne = scene.clinician("Dr Cayenne", "America/Cayenne", True)
    gone = scene.clinician("Dr Parti", "Europe/Paris", False)
    scene.rule(cayenne, 5, time(9), time(12))
    scene.rule(gone, 5, time(9), time(12))
    scene.off(cayenne, datetime(2026, 11, 20, 10), datetime(2026, 11, 20, 11))
    scene.off(cayenne, datetime(2026, 10, 1, 10), datetime(2026, 10, 1, 11))
    start, end = Range.WEEK.window(NOW)

    (schedule,) = scene.queries.schedules(start, end)

    assert schedule.time_zone == "America/Cayenne"
    assert [(r.weekday, r.start, r.end) for r in schedule.rules] == [(5, time(9), time(12))]
    assert schedule.absences == (
        Absence(
            scene.at(cayenne, datetime(2026, 11, 20, 10)),
            scene.at(cayenne, datetime(2026, 11, 20, 11)),
        ),
    )
