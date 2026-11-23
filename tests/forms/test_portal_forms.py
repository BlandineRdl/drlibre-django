from datetime import date

from drlibre.booking.application.ports.inbound import MAX_CANCELLATION_REASON
from drlibre.interfaces.web.forms.portal import CancelForm, ProfileForm, WaitlistJoinForm
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.markup import attributes

KIND = Id()
CLINICIAN = Id()


def join(data: dict[str, str] | None) -> WaitlistJoinForm:
    return WaitlistJoinForm(
        data, types=((str(KIND), "Consultation"),), clinicians=((str(CLINICIAN), "Dr Ana"),)
    )


def test_a_reason_over_the_limit_is_refused_on_its_field_and_focused() -> None:
    """Story « annule » : motif obligatoire, borné."""
    form = CancelForm({"reason": "x" * (MAX_CANCELLATION_REASON + 1)})

    assert not form.is_valid()
    assert list(form.errors) == ["reason"]
    assert "autofocus" in attributes(form.render(), "field-reason")


def test_the_profile_starts_from_the_stored_birth_date_as_a_date_input_reads_it() -> None:
    """Story « profil » : téléphone et date de naissance modifiables, facultatifs."""
    form = ProfileForm(initial={"phone": "0601020304", "birth_date": date(1990, 5, 17)})

    html = form.render()
    assert attributes(html, "field-birth_date")["value"] == "1990-05-17"
    assert attributes(html, "field-phone")["type"] == "tel"
    assert ProfileForm({"phone": "", "birth_date": ""}).is_valid()


def test_a_join_gives_the_use_case_ids_and_days() -> None:
    """Story « le patient s'inscrit » : type, praticien facultatif et fenêtre de dates."""
    form = join(
        {"appointment_type_id": str(KIND), "from_date": "2026-11-23", "to_date": "2026-11-27"}
    )

    assert form.is_valid()
    assert form.cleaned_data == {
        "appointment_type_id": KIND,
        "clinician_id": None,
        "from_date": date(2026, 11, 23),
        "to_date": date(2026, 11, 27),
    }


def test_a_join_refuses_an_unknown_type_and_a_missing_date() -> None:
    """Story « le patient s'inscrit » : une date manquante est refusée."""
    form = join({"appointment_type_id": str(Id()), "from_date": "2026-11-23"})

    assert not form.is_valid()
    assert set(form.errors) == {"appointment_type_id", "to_date"}
    assert form.errors["to_date"] == ["Saisissez une date."]


def test_an_inverted_window_refused_by_the_use_case_lands_on_its_last_day() -> None:
    """Story « le patient s'inscrit » : une fenêtre inversée est refusée."""
    form = join(
        {"appointment_type_id": str(KIND), "from_date": "2026-11-27", "to_date": "2026-11-23"}
    )
    assert form.is_valid()
    fields = [{"field": "to_date", "message": "Après le premier jour."}]

    form.refuse(DomainError(ErrorCode.INVALID_INPUT, "Corrigez.", {"fields": fields}))

    html = form.render()
    assert 'href="#field-to_date"' in html
    assert "autofocus" in attributes(html, "field-to_date")
    assert html.index("Choisir…") < html.index("Consultation")
