from drlibre.interfaces.web.forms.auth import LinkRequestForm, PasswordChangeForm, SignInForm
from drlibre.interfaces.web.presenters.auth import (
    LINK_SENT_MESSAGE,
    link_continue,
    link_refused,
    link_request_page,
    link_sent,
    password_page,
    sign_in_page,
)
from drlibre.interfaces.web.presenters.console import console_nav
from drlibre.shared_kernel.errors import DomainError, ErrorCode


def test_password_page_names_a_forced_change() -> None:
    page = password_page(PasswordChangeForm(), forced=True)

    assert (page.title, page.action) == ("Choisissez votre mot de passe", "/account/password")
    assert password_page(PasswordChangeForm(), forced=False).title == "Changer mon mot de passe"


def test_sign_in_page_posts_to_sign_in() -> None:
    page = sign_in_page(SignInForm())

    assert (page.action, page.submit_label) == ("/sign-in", "Se connecter")


def test_console_nav_marks_the_current_section_only() -> None:
    nav = console_nav("/console/rooms/12/edit")

    assert [link.label for link in nav if link.current] == ["Salles"]


def test_link_request_page_posts_the_link_email() -> None:
    page = link_request_page(LinkRequestForm({"link_email": "lea@"}))

    assert page.action == "/sign-in/link/request"
    assert "link_email" in page.form.fields


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
