from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from itertools import cycle

import pytest

from drlibre.bootstrap.container import Container, real_adapters, wire
from drlibre.identity.domain.user import Role
from drlibre.reporting.domain.dashboard import Range
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.builders_reporting import ActivityScene, real_activity
from tests.fakes.clock import FixedClock

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
STATUSES = ("BOOKED", "CHECKED_IN", "COMPLETED", "NO_SHOW", "CANCELLED")
SOURCES = ("ONLINE", "ROUND_ROBIN", "STAFF")


@dataclass(frozen=True, slots=True)
class Booked:
    clinician: Id
    day: date
    minutes: int
    status: str
    source: str


def app() -> Container:
    return wire(real_adapters(FixedClock(NOW)))


def admin() -> Id:
    return stored_user(Role.ADMIN).id


def stored_activity(scene: ActivityScene) -> tuple[list[Booked], dict[Id, str]]:
    """Paris and Cayenne clinicians, every status and source over 40 days, rules and time off."""
    names = {
        scene.clinician("Dr Paris", "Europe/Paris", True): "Dr Paris",
        scene.clinician("Dr Cayenne", "America/Cayenne", True): "Dr Cayenne",
    }
    booked: list[Booked] = []
    kinds = cycle((s, src, m) for s in STATUSES for src in SOURCES for m in (20, 30, 45))
    for clinician in names:
        today = NOW.astimezone(scene.zones[clinician]).date()
        for back in range(40):
            day = today - timedelta(days=back)
            for hour in (9, 23) if back % 3 == 0 else (9,):
                status, source, minutes = next(kinds)
                local = datetime.combine(day, time(hour, 15))
                scene.appointment(clinician, local, minutes, status, source)
                booked.append(Booked(clinician, day, minutes, status, source))
        for weekday in range(1, 6):
            scene.rule(clinician, weekday, time(9), time(17))
        scene.off(clinician, datetime(2026, 11, 18, 12), datetime(2026, 11, 19, 10))
    for status in ("WAITING", "OFFERED", "BOOKED", "EXPIRED", "WAITING"):
        scene.waitlist(status)
    return booked, names


def in_range(scene: ActivityScene, booked: list[Booked], period: Range) -> list[Booked]:
    def inside(b: Booked) -> bool:
        return b.day in period.days(NOW.astimezone(scene.zones[b.clinician]).date())

    return [b for b in booked if inside(b)]


def expected_available(period: Range) -> int:
    """Weekday rules of 8 h; the time off removes 5 h on the 18th and 1 h on the 19th."""
    days = period.days(NOW.date())
    working = sum(1 for d in days if d.isoweekday() <= 5)
    off = (5 if date(2026, 11, 18) in days else 0) + (1 if date(2026, 11, 19) in days else 0)
    return 2 * (working * 8 - off) * 60


@pytest.mark.parametrize("period", list(Range))
def test_each_figure_equals_its_definition(period: Range) -> None:
    """Story indicateurs : chaque indicateur égal à sa définition §13, sur les deux fuseaux."""
    scene = real_activity()
    booked, _ = stored_activity(scene)
    rows = in_range(scene, booked, period)
    kept = [b for b in rows if b.status != "CANCELLED"]
    active = [b for b in kept if b.status != "NO_SHOW"]

    shown = app().view_dashboard.execute(actor_id=admin(), period=period)

    assert shown.appointments == len(kept)
    assert shown.cancellations == len(rows) - len(kept)
    assert shown.no_show_rate.num == sum(b.status == "NO_SHOW" for b in kept)
    assert shown.no_show_rate.den == len(kept)
    assert shown.online_share.num == sum(b.source != "STAFF" for b in kept)
    assert shown.utilisation.num == sum(b.minutes for b in active)
    assert shown.utilisation.den == expected_available(period)
    assert shown.waitlist_size == 3


def test_days_and_busiest_follow_the_local_day_of_each_hospital() -> None:
    """Story jours et praticiens chargés : un compte par jour local, classement par nombre."""
    scene = real_activity()
    booked, names = stored_activity(scene)
    rows = [b for b in in_range(scene, booked, Range.MONTH) if b.status != "CANCELLED"]

    shown = app().view_dashboard.execute(actor_id=admin(), period=Range.MONTH)

    counted = {d.day: d.count for d in shown.per_day if d.count}
    assert counted == {day: sum(b.day == day for b in rows) for day in {b.day for b in rows}}
    assert len(shown.per_day) >= Range.MONTH.length
    per_clinician = {c: sum(b.clinician == c for b in rows) for c in names}
    ranked = sorted(per_clinician.items(), key=lambda kv: (-kv[1], names[kv[0]]))
    assert [(c.clinician_id, c.count) for c in shown.busiest] == ranked


def test_a_late_appointment_counts_in_the_local_day_of_cayenne() -> None:
    """Story indicateurs : 23:30 à Cayenne est le lendemain en UTC, compté le jour local."""
    scene = real_activity()
    cayenne = scene.clinician("Dr Cayenne", "America/Cayenne", True)
    scene.appointment(cayenne, datetime(2026, 11, 19, 23, 30), 30, "BOOKED", "ONLINE")

    shown = app().view_dashboard.execute(actor_id=admin(), period=Range.TODAY)

    assert shown.appointments == 0
    week = app().view_dashboard.execute(actor_id=admin(), period=Range.WEEK)
    assert [(d.day, d.count) for d in week.per_day if d.count] == [(date(2026, 11, 19), 1)]


def test_without_activity_every_ratio_is_not_available() -> None:
    """Story indicateurs : un dénominateur nul affiche « n/a », jamais 0 %."""
    shown = app().view_dashboard.execute(actor_id=admin(), period=Range.WEEK)

    assert [r.percent for r in (shown.utilisation, shown.no_show_rate, shown.online_share)] == [
        None,
        None,
        None,
    ]
    assert shown.busiest == ()


@pytest.mark.parametrize("role", [Role.PATIENT, Role.CLINICIAN])
def test_only_an_admin_views_the_dashboard(role: Role) -> None:
    """Spec 10 : le tableau de bord est réservé à l'admin."""
    with pytest.raises(DomainError) as refused:
        app().view_dashboard.execute(actor_id=stored_user(role).id, period=Range.WEEK)

    assert refused.value.code is ErrorCode.FORBIDDEN
