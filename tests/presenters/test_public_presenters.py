from datetime import UTC, date, datetime

from drlibre.interfaces.web.presenters.public import provider_page_view
from drlibre.search.application.ports.inbound import BookableType, ProviderDetail, ProviderWeek
from drlibre.shared_kernel.ids import Id

KIND = Id()
CLINICIAN = Id()


def week(
    starts: tuple[datetime, ...], previous: date | None, following: date | None
) -> ProviderWeek:
    detail = ProviderDetail(
        id=CLINICIAN,
        full_name="Dr Alice Martin",
        title="Cardiologue",
        specialty_name="Cardiologie",
        bio="Cardiologue interventionnelle",
        hospital_id=Id(),
        hospital_name="Hôpital Nord",
        department_id=Id(),
        department_name="Cardiologie",
        city="Lille",
        time_zone="Europe/Paris",
        types=(BookableType(KIND, "Consultation", 20),),
    )
    return ProviderWeek(detail, KIND, date(2026, 11, 23), previous, following, starts)


def test_the_week_strip_runs_monday_to_sunday_in_the_hospital_zone() -> None:
    """Story page praticien : bandeau du lundi au dimanche, en heure de l'hôpital."""
    view = provider_page_view(
        week((datetime(2026, 11, 24, 23, 30, tzinfo=UTC),), date(2026, 11, 16), None)
    )

    assert [d.label for d in view.days] == [
        "lun. 23/11",
        "mar. 24/11",
        "mer. 25/11",
        "jeu. 26/11",
        "ven. 27/11",
        "sam. 28/11",
        "dim. 29/11",
    ]
    wednesday = view.days[2]
    assert [s.label for s in wednesday.slots] == ["00:30"]
    assert view.days[0].empty_text == "Aucun créneau"
    assert view.week_label == "Semaine du lun. 23/11 au dim. 29/11"


def test_week_navigation_is_offered_only_inside_the_horizon() -> None:
    """Story page praticien : semaines précédente et suivante, limitées à l'horizon."""
    view = provider_page_view(week((), date(2026, 11, 16), None))

    assert view.previous_url == f"/providers/{CLINICIAN}?type={KIND}&week=2026-11-16"
    assert view.next_url == ""
    assert view.empty_week_text == "Aucun créneau libre cette semaine."
