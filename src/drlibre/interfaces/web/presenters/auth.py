from dataclasses import dataclass

from drlibre.interfaces.web.forms.auth import LinkRequestForm, PasswordChangeForm, SignInForm
from drlibre.interfaces.web.presenters.form_page import FormPage
from drlibre.shared_kernel.booking_policy import LINK_LIFETIME
from drlibre.shared_kernel.errors import DomainError, ErrorCode

LINK_SENT_MESSAGE = (
    "Si cette adresse est celle d'un compte patient, "
    f"un lien de connexion valable {int(LINK_LIFETIME.total_seconds() // 60)} minutes "
    "vient d'être envoyé."
)
NO_LINK_MESSAGE = "Ce lien n'est pas valable. Demandez-en un nouveau."


def sign_in_page(form: SignInForm) -> FormPage:
    return FormPage("Se connecter", "/sign-in", "Se connecter", form)


def password_page(form: PasswordChangeForm, *, forced: bool) -> FormPage:
    title = "Choisissez votre mot de passe" if forced else "Changer mon mot de passe"
    return FormPage(title, "/account/password", "Enregistrer", form)


def link_request_page(form: LinkRequestForm) -> FormPage:
    return FormPage(
        "Recevoir un lien de connexion", "/sign-in/link/request", "Recevoir un lien", form
    )


@dataclass(frozen=True, slots=True)
class LinkSentView:
    title: str
    message: str


@dataclass(frozen=True, slots=True, kw_only=True)
class LinkContinueView:
    """The page a link opens: one button holding the token, or a refusal with a new request."""

    title: str
    action: str
    token: str = ""
    submit_label: str
    message: str
    request_form: FormPage | None


def link_sent() -> LinkSentView:
    return LinkSentView(title="Vérifiez vos emails", message=LINK_SENT_MESSAGE)


def link_continue(token: str) -> LinkContinueView:
    return LinkContinueView(
        title="Votre lien de connexion",
        action="/sign-in/link",
        token=token,
        submit_label="Continuer",
        message="",
        request_form=None,
    )


def link_refused(error: DomainError) -> LinkContinueView:
    return LinkContinueView(
        title="Votre lien de connexion",
        action="/sign-in/link",
        submit_label="Continuer",
        message=error.message,
        request_form=link_request_page(LinkRequestForm()),
    )


def link_missing() -> LinkContinueView:
    return link_refused(DomainError(ErrorCode.UNAUTHENTICATED, NO_LINK_MESSAGE))
