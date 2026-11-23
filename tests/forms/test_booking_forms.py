from drlibre.interfaces.web.forms.booking import CodeForm, DetailsForm
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from tests.markup import attributes, described_by

DETAILS = {
    "full_name": "Ana Martin",
    "birth_date": "1990-05-17",
    "email": "ana@example.org",
    "accepted_terms": "on",
}


def refusal(*fields: tuple[str, str]) -> DomainError:
    items = [{"field": name, "message": message} for name, message in fields]
    return DomainError(ErrorCode.INVALID_INPUT, "Corrigez les champs.", {"fields": items})


def test_refused_details_tie_each_error_to_its_field_and_focus_the_first() -> None:
    """Story réservation : erreurs rattachées aux champs, focus sur le premier invalide."""
    form = DetailsForm({**DETAILS, "email": "x@example.org"})
    assert form.is_valid()

    form.refuse(
        refusal(("email", "Saisissez une adresse email valide."), ("full_name", "Trop long."))
    )

    html = form.render()
    assert "autofocus" in attributes(html, "field-full_name")
    assert "autofocus" not in attributes(html, "field-email")
    assert described_by(html, "field-email") == ["field-email_error"]


def test_a_re_rendered_birth_date_keeps_the_value_a_date_input_reads() -> None:
    """Story réservation : la date de naissance saisie reste dans le champ date."""
    form = DetailsForm({**DETAILS, "full_name": ""})

    assert not form.is_valid()
    assert attributes(form.render(), "field-birth_date")["value"] == "1990-05-17"


def test_missing_details_are_refused_in_french_phone_and_reason_being_optional() -> None:
    """Story réservation : téléphone et motif facultatifs, le reste obligatoire."""
    form = DetailsForm({"accepted_terms": "on"})

    assert not form.is_valid()
    assert set(form.errors) == {"full_name", "birth_date", "email"}
    assert form.errors["email"] == ["Ce champ est obligatoire."]
    assert "(facultatif)" in form.render().split('id="field-phone"')[0]


def test_a_wrong_code_is_tied_to_the_code_field_and_focused() -> None:
    """Story réservation : code incorrect, erreur sur le champ."""
    form = CodeForm({"code": "000000"})
    assert form.is_valid()

    form.refuse(refusal(("code", "Code incorrect.")))

    code = attributes(form.render(), "field-code")
    assert (code["aria-invalid"], "autofocus" in code) == ("true", True)
    assert code["autocomplete"] == "one-time-code"
