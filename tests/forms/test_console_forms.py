from datetime import date

from drlibre.interfaces.web.forms.console import HospitalForm, UserForm, WaitlistAddForm
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from tests.markup import attributes, described_by

KIND = Id()
HOSPITAL = {
    "name": "Hôpital Nord",
    "code": "HNORD",
    "street": "1 rue de la Paix",
    "postal_code": "59000",
    "city": "Lille",
    "country": "France",
    "phone": "+33 3 20 00 00 00",
    "time_zone": "Mars/Olympus",
    "active": "on",
}


def test_an_unknown_time_zone_is_described_focused_and_summarised_on_its_field() -> None:
    """§10 console : un champ invalide est signalé sur le champ et dans le résumé."""
    form = HospitalForm(HOSPITAL)
    assert form.is_valid()
    fields = [{"field": "time_zone", "message": "Fuseau horaire inconnu."}]

    form.refuse(DomainError(ErrorCode.INVALID_INPUT, "Corrigez.", {"fields": fields}))

    html = form.render()
    assert "autofocus" in attributes(html, "field-time_zone")
    assert "field-time_zone_error" in described_by(html, "field-time_zone")
    assert 'href="#field-time_zone"' in html
    assert form.posted()["time_zone"] == "Mars/Olympus"


def test_a_refused_new_account_never_shows_its_temporary_password_again() -> None:
    """Comptes utilisateurs : mot de passe temporaire à la création seulement."""
    form = UserForm(
        {"full_name": "Ana Bel", "email": "pas-un-email", "role": "CLINICIAN", "active": "on"}
        | {"temporary_password": "temporary-pass-1"},
        creating=True,
    )

    assert not form.is_valid()
    html = form.render()
    assert "temporary-pass-1" not in html
    assert "value" not in attributes(html, "field-temporary_password")
    assert "temporary_password" not in UserForm(creating=False).fields


def test_a_staff_join_names_the_patient_first_and_gives_the_use_case_ids_and_days() -> None:
    """Liste d'attente console : l'admin inscrit un patient par son email."""
    form = WaitlistAddForm(
        {
            "patient_email": "ana@example.org",
            "appointment_type_id": str(KIND),
            "from_date": "2026-11-23",
            "to_date": "2026-11-27",
        },
        types=((str(KIND), "Consultation"),),
        clinicians=(),
    )

    assert form.is_valid()
    assert next(iter(form.fields)) == "patient_email"
    assert form.cleaned_data == {
        "patient_email": "ana@example.org",
        "appointment_type_id": KIND,
        "clinician_id": None,
        "from_date": date(2026, 11, 23),
        "to_date": date(2026, 11, 27),
    }
