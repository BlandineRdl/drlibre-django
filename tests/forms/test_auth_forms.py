from drlibre.interfaces.web.forms.auth import PasswordChangeForm, SignInForm
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.validation import invalid_field
from tests.markup import attributes, described_by


def test_refused_sign_in_keeps_the_email_never_the_password() -> None:
    form = SignInForm({"email": "ana@example.org", "password": "secret-password"})
    assert form.is_valid()

    form.refuse(DomainError(ErrorCode.UNAUTHENTICATED, "Email ou mot de passe incorrect."))

    html = form.render()
    assert "<strong>Email ou mot de passe incorrect.</strong>" in html
    assert attributes(html, "field-email")["value"] == "ana@example.org"
    assert "value" not in attributes(html, "field-password")
    assert "secret-password" not in html


def test_invalid_field_is_described_focused_and_summarised() -> None:
    form = PasswordChangeForm({"current_password": "my-password-1", "new_password": "x" * 12})
    assert form.is_valid()

    form.refuse(invalid_field("new_password", "De 10 à 72 caractères."))

    html = form.render()
    new = attributes(html, "field-new_password")
    assert new["aria-invalid"] == "true"
    assert "autofocus" in new
    assert "autofocus" not in attributes(html, "field-current_password")
    assert described_by(html, "field-new_password") == [
        "field-new_password_helptext",
        "field-new_password_error",
    ]
    assert 'href="#field-new_password">Nouveau mot de passe : De 10 à 72 caractères.' in html


def test_empty_fields_are_refused_in_french_and_the_first_is_focused() -> None:
    form = SignInForm({"email": "", "password": ""})

    assert not form.is_valid()
    html = form.render()
    assert form.errors["email"] == ["Ce champ est obligatoire."]
    assert "autofocus" in attributes(html, "field-email")
    assert "autofocus" not in attributes(html, "field-password")
    assert attributes(html, "field-email_error")


def test_untouched_form_shows_no_error_and_no_focus() -> None:
    html = SignInForm().render()

    assert 'role="alert"' not in html
    assert "autofocus" not in html


def test_a_refused_sign_in_shows_its_message_without_an_empty_field_list() -> None:
    form = SignInForm({"email": "ana@example.org", "password": "wrong-password"})
    assert form.is_valid()

    form.refuse(DomainError(ErrorCode.INVALID_INPUT, "Email ou mot de passe incorrect."))

    html = form.render()
    assert "Email ou mot de passe incorrect." in html
    assert "<ul>" not in html
