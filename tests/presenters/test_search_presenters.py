from datetime import UTC, datetime

from drlibre.interfaces.web.presenters.search import (
    Kind,
    hospital_result,
    provider_result,
    search_url,
)
from drlibre.search.application.ports.inbound import (
    FirstSlot,
    HospitalResult,
    NextSlots,
    ProviderResult,
    SearchCriteria,
)
from drlibre.shared_kernel.ids import Id

KIND = Id()
CLINICIAN = Id()
DEPARTMENT = Id()
START = datetime(2026, 11, 23, 8, tzinfo=UTC)


def provider(next_slots: NextSlots | None) -> ProviderResult:
    return ProviderResult(
        id=CLINICIAN,
        full_name="Dr Alice Martin",
        title="Cardiologue",
        specialty_name="Cardiologie",
        hospital_id=Id(),
        hospital_name="Hôpital Nord",
        department_name="Cardiologie",
        city="Lille",
        time_zone="Europe/Paris",
        next_slots=next_slots,
        distance_km=None,
    )


def test_a_provider_card_shows_local_starts_as_booking_links_and_the_type() -> None:
    """Story résultats : 3 débuts libres en heure de l'hôpital, chacun un lien de réservation."""
    view = provider_result(provider(NextSlots(KIND, "Consultation", 20, (START,))))

    assert view.slots_heading == "Consultation 20 min"
    assert [s.label for s in view.slots] == ["lun. 23/11 09:00"]
    assert view.slots[0].url == (
        f"/booking/new?type={KIND}&clinician={CLINICIAN}&start=2026-11-23T08:00:00Z"
    )
    assert "Heure de Paris" in view.lines
    assert view.empty_text == ""


def test_a_provider_without_slot_says_so() -> None:
    """Story résultats : le texte « Aucune disponibilité dans les 90 prochains jours »."""
    view = provider_result(provider(None))

    assert view.slots == ()
    assert view.empty_text == "Aucune disponibilité dans les 90 prochains jours"


def test_a_hospital_card_links_its_first_slot_to_first_available_booking() -> None:
    """Story résultats : le premier créneau d'un hôpital réserve le premier disponible."""
    hospital = HospitalResult(
        id=Id(),
        name="Hôpital Nord",
        street="1 rue de la Paix",
        postal_code="59000",
        city="Lille",
        time_zone="Europe/Paris",
        specialties=("Cardiologie",),
        providers=2,
        providers_with_slots=1,
        first_slot=FirstSlot(START, KIND, "Consultation", DEPARTMENT),
        distance_km=None,
    )

    view = hospital_result(hospital)

    assert view.slots[0].url == (
        f"/booking/new?type={KIND}&department={DEPARTMENT}&start=2026-11-23T08:00:00Z"
    )
    assert "2 praticiens réservables" in view.lines
    assert "1 praticien avec un créneau libre" in view.lines


def test_the_address_keeps_every_value_and_omits_the_defaults() -> None:
    """Story recherche : texte, filtres, tri et taille vivent dans l'adresse."""
    criteria = SearchCriteria.parse(
        {"q": "card", "window": "7d", "moment": "evening", "sort": "name", "size": "10"}
    )

    assert search_url(criteria, Kind.HOSPITALS, page=2) == (
        "/?list=hospitals&q=card&window=7d&moment=evening&sort=name&size=10&page=2"
    )
    assert search_url(SearchCriteria(), Kind.PROVIDERS) == "/"
