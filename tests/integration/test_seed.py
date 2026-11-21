import uuid
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.apps import apps

from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.booking.infrastructure.django.models import AppointmentRecord, WaitlistEntryRecord
from drlibre.bootstrap.container import container
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.organisation.infrastructure.django.models import (
    AppointmentTypeRecord,
    ClinicianProfileRecord,
)
from drlibre.reporting.domain.dashboard import Range, Ratio
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel, TimeOffModel
from drlibre.shared_kernel.ids import Id
from scripts import seed

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def counts() -> dict[str, int]:
    labels = ("identity", "organisation", "scheduling")
    return {
        model.__name__: model._default_manager.count()
        for label in labels
        for model in apps.get_app_config(label).get_models()
    }


def test_the_demo_seed_can_run_again_without_duplicating_rows() -> None:
    """Spec §16: a seed that can be run again without duplicating rows, one sign-in per role."""
    seed.main()
    first = counts()

    seed.main()

    assert counts() == first
    assert first["HospitalRecord"] >= 2
    roles = set(
        UserRecord.objects.filter(email__endswith="@drlibre.localhost").values_list(
            "role", flat=True
        )
    )
    assert roles == {"ADMIN", "CLINICIAN", "PATIENT"}
    admin = UserRecord.objects.get(email="admin@drlibre.localhost")
    seeded = AuditEntryRecord.objects.filter(entity_type="hospital", action="hospital.created")
    assert set(seeded.values_list("actor_id", flat=True)) == {admin.id}


def test_the_second_demo_clinician_shares_the_demo_department_once_even_after_a_reseed() -> None:
    """Epic E6: a second clinician of HNORD-CARD with its own room and rules, seeded once."""
    seed.main()
    seed.main()

    users = UserRecord.objects.filter(email=seed.SECOND_CLINICIAN_EMAIL)
    (user,) = users
    profiles = ClinicianProfileRecord.objects.filter(user_id=user.id)
    (profile,) = profiles
    demo = UserRecord.objects.get(email=seed.CLINICIAN_EMAIL)
    first = ClinicianProfileRecord.objects.get(user_id=demo.id)
    assert (user.role, profile.department_id) == ("CLINICIAN", first.department_id)
    assert profile.default_room_id != first.default_room_id
    rules = container().availability_queries.rules_of(Id(profile.id))
    assert len(rules) == len(seed.DEMO_RULES)


def test_the_demo_clinician_has_free_slots_after_the_seed() -> None:
    """Epic E2: the seeded weekly rules give the demo clinician bookable slots."""
    seed.main()
    consult = AppointmentTypeRecord.objects.get(code="HNORD-CONSULT")
    user = UserRecord.objects.get(email="clinicien@drlibre.localhost")
    profile = container().reference_queries.clinician_profile_of(Id(user.id))
    assert profile is not None
    start = datetime.now(UTC)

    slots = container().find_free_slots.execute(
        appointment_type_id=Id(consult.id),
        clinician_id=profile.id,
        start=start,
        end=start + timedelta(days=7),
    )

    assert slots


def test_the_demo_clinician_sees_the_seeded_appointments_on_the_next_working_day() -> None:
    """Epic E6: the seed books the passwordless patient on the demo clinician's next day, once."""
    seed.main()
    seed.main()
    user = UserRecord.objects.get(email="clinicien@drlibre.localhost")
    day = seed._next_working_day(datetime.now(UTC)).date()

    view = container().clinician_day.execute(actor_id=Id(user.id), day=day)

    entries = [e for hour in view.hours for e in hour.entries]
    assert len(entries) == seed.DEMO_APPOINTMENTS
    assert {e.patient_name for e in entries} == {"Victor Visiteur"}
    assert {e.appointment.status.value for e in entries} == {"BOOKED"}


def test_the_load_seed_never_double_books_a_room_a_clinician_or_a_patient(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spec §14 load: seeded appointments respect the placement rules a booking enforces."""
    monkeypatch.setattr(seed, "LOAD_CLINICIANS", 40)
    monkeypatch.setattr(seed, "LOAD_PATIENTS", 400)
    monkeypatch.setattr(seed, "LOAD_APPOINTMENTS_PER_CLINICIAN", 60)

    seed.main(size="load")
    seed.main(size="load")

    rows = list(
        AppointmentRecord.objects.filter(clinician__department__code__startswith="LOAD-").values(
            "patient_id", "clinician_id", "room_id", "start"
        )
    )
    assert len(rows) == 40 * 60
    for key in ("patient_id", "clinician_id", "room_id"):
        slots = [(row[key], row["start"]) for row in rows]
        assert len(set(slots)) == len(slots), key


def test_the_demo_clinician_is_named_once_with_an_honorific_title_even_after_a_reseed() -> None:
    """Spec §3.1: the profile title is the honorific; the name stays in the user record."""
    seed.main()
    user = UserRecord.objects.get(email="clinicien@drlibre.localhost")
    profile = ClinicianProfileRecord.objects.get(user_id=user.id)
    assert (user.full_name, profile.title) == ("Claire Martin", "Dr")
    # A database seeded before the fix held the name in both places.
    UserRecord.objects.filter(id=user.id).update(full_name="Dr Claire Martin")
    ClinicianProfileRecord.objects.filter(id=profile.id).update(title="Dr Claire Martin")

    seed.main()

    user.refresh_from_db()
    profile.refresh_from_db()
    assert (user.full_name, profile.title) == ("Claire Martin", "Dr")


def test_the_demo_seed_fills_the_past_week_in_every_closed_status_and_source_once() -> None:
    """Epic E7: the dashboard shows non-zero figures on the demo, a reseed adds nothing."""
    seed.main()
    seed.main()
    now = datetime.now(UTC)
    past = AppointmentRecord.objects.filter(
        start__gte=now - timedelta(days=seed.PAST_DAYS + 1), start__lt=now
    )
    rows = list(past.values_list("id", "status", "source"))

    assert len({r[0] for r in rows}) == len(rows)
    assert {"COMPLETED", "CANCELLED", "NO_SHOW"} <= {r[1] for r in rows}
    assert {"ONLINE", "ROUND_ROBIN", "STAFF"} <= {r[2] for r in rows}
    waiting = WaitlistEntryRecord.objects.filter(status="WAITING")
    assert waiting.values("patient_id").distinct().count() == 2
    assert waiting.count() == 2


def test_the_demo_seed_holds_an_appointment_in_every_status() -> None:
    """Epic E7 Success Evidence: the seed holds appointments in every status, once."""
    seed.main()
    seed.main()

    statuses = set(AppointmentRecord.objects.values_list("status", flat=True))
    checked_in = AppointmentRecord.objects.filter(status="CHECKED_IN")

    assert statuses == {"BOOKED", "CHECKED_IN", "COMPLETED", "CANCELLED", "NO_SHOW"}
    assert checked_in.count() == 1


def _zones() -> dict[uuid.UUID, ZoneInfo]:
    profiles = ClinicianProfileRecord.objects.values_list("id", "department__hospital__time_zone")
    return {profile: ZoneInfo(zone) for profile, zone in profiles}


def _days_ago(start: datetime, now: datetime, zone: ZoneInfo) -> int:
    return (now.astimezone(zone).date() - start.astimezone(zone).date()).days


def _available_minutes(period: Range, now: datetime, zones: dict[uuid.UUID, ZoneInfo]) -> int:
    active = set(
        UserRecord.objects.filter(role="CLINICIAN", active=True).values_list("id", flat=True)
    )
    total = 0.0
    for profile in ClinicianProfileRecord.objects.filter(user_id__in=active):
        zone = zones[profile.id]
        off = list(TimeOffModel.objects.filter(clinician_id=profile.id))
        for day in period.days(now.astimezone(zone).date()):
            for rule in AvailabilityRuleModel.objects.filter(clinician_id=profile.id):
                # Weekday 0 is Sunday in scheduling.
                if day.isoweekday() % 7 != rule.weekday or day < rule.valid_from:
                    continue
                if rule.valid_to is not None and day > rule.valid_to:
                    continue
                start = datetime.combine(day, rule.start, tzinfo=zone)
                end = datetime.combine(day, rule.end, tzinfo=zone)
                total += (end - start).total_seconds()
                for t in off:
                    total -= max(0.0, (min(end, t.end) - max(start, t.start)).total_seconds())
    return int(total // 60)


def test_each_dashboard_figure_on_the_seed_matches_its_definition() -> None:
    """Spec §13: each figure recomputed from the seeded rows equals the dashboard's."""
    seed.main()
    admin = UserRecord.objects.get(email=seed.ADMIN_EMAIL)
    period = Range.WEEK

    shown = container().view_dashboard.execute(actor_id=Id(admin.id), period=period)
    now = datetime.now(UTC)
    zones = _zones()
    in_range = [
        a
        for a in AppointmentRecord.objects.all()
        if 0 <= _days_ago(a.start, now, zones[a.clinician_id]) < period.length
    ]
    kept = [a for a in in_range if a.status != "CANCELLED"]
    active = [a for a in kept if a.status != "NO_SHOW"]
    minutes = int(sum((a.end - a.start).total_seconds() for a in active) // 60)
    online = [a for a in kept if a.source in ("ONLINE", "ROUND_ROBIN")]
    no_shows = [a for a in kept if a.status == "NO_SHOW"]
    waiting = WaitlistEntryRecord.objects.filter(status__in=("WAITING", "OFFERED")).count()

    assert shown.appointments == len(kept) > 0
    assert shown.cancellations == len(in_range) - len(kept) > 0
    assert shown.utilisation == Ratio(minutes, _available_minutes(period, now, zones))
    assert shown.no_show_rate == Ratio(len(no_shows), len(kept))
    assert shown.online_share == Ratio(len(online), len(kept))
    assert shown.waitlist_size == waiting > 0
