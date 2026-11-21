from drlibre.interfaces.web.presenters.auth import (
    LINK_SENT_MESSAGE,
    link_continue,
    link_refused,
    link_request_form,
    link_sent,
    password_form,
    sign_in_form,
)
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.validation import invalid_field


def test_refused_sign_in_keeps_the_email_never_the_password() -> None:
    error = DomainError(ErrorCode.UNAUTHENTICATED, "Email ou mot de passe incorrect.")

    form = sign_in_form({"email": "ana@example.org", "password": "secret-123"}, error)

    email, password = form.fields
    assert form.has_errors
    assert form.message == "Email ou mot de passe incorrect."
    assert email.value == "ana@example.org"
    assert password.value == ""


def test_invalid_field_is_described_focused_and_summarised() -> None:
    error = invalid_field("new_password", "De 10 à 72 caractères.")

    form = password_form(forced=True, error=error)

    current, new = form.fields
    assert form.title == "Choisissez votre mot de passe"
    assert not current.autofocus
    assert new.autofocus
    assert new.error == "De 10 à 72 caractères."
    assert new.described_by == "help-new_password error-new_password"
    assert [(e.field, e.label) for e in form.errors] == [("new_password", "Nouveau mot de passe")]


def test_untouched_form_shows_no_error_and_no_focus() -> None:
    form = sign_in_form({})

    assert not form.has_errors
    assert not any(field.autofocus for field in form.fields)


def test_console_nav_marks_the_current_section_only() -> None:
    nav = console_nav("/console/rooms/12/edit")

    assert [link.label for link in nav if link.current] == ["Salles"]


def test_link_request_form_keeps_the_email_and_names_its_field() -> None:
    error = invalid_field("link_email", "Saisissez une adresse email valide.")

    form = link_request_form({"link_email": "lea@"}, error)

    (email,) = form.fields
    assert form.action == "/sign-in/link/request"
    assert email.name == "link_email"
    assert email.value == "lea@"
    assert email.autofocus


def test_continue_page_carries_the_token_in_a_button_and_no_request_form() -> None:
    view = link_continue("abc")

    assert (view.token, view.submit_label, view.action) == ("abc", "Continuer", "/sign-in/link")
    assert view.message == ""
    assert view.request_form is None


def test_refused_link_drops_the_token_and_offers_a_new_request() -> None:
    error = DomainError(ErrorCode.UNAUTHENTICATED, "Ce lien n'est plus valable.")

    view = link_refused(error)

    assert view.token == ""
    assert view.message == "Ce lien n'est plus valable."
    assert view.request_form is not None
    assert view.request_form.submit_label == "Recevoir un lien"


def test_sent_message_is_the_same_whatever_the_address() -> None:
    assert link_sent().message == LINK_SENT_MESSAGE
