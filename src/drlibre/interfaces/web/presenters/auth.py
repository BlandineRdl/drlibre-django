from collections.abc import Mapping
from dataclasses import dataclass

from drlibre.interfaces.web.presenters.forms import FieldSpec, FormView, build_form
from drlibre.shared_kernel.booking_policy import LINK_LIFETIME
from drlibre.shared_kernel.errors import DomainError, ErrorCode

SIGN_IN_FIELDS = (
    FieldSpec("email", "Email", kind="email", autocomplete="username"),
    FieldSpec("password", "Mot de passe", kind="password", autocomplete="current-password"),
)
LINK_FIELDS = (FieldSpec("link_email", "Email", kind="email", autocomplete="email"),)
LINK_SENT_MESSAGE = (
    "Si cette adresse est celle d'un compte patient, "
    f"un lien de connexion valable {int(LINK_LIFETIME.total_seconds() // 60)} minutes "
    "vient d'être envoyé."
)
NO_LINK_MESSAGE = "Ce lien n'est pas valable. Demandez-en un nouveau."
PASSWORD_FIELDS = (
    FieldSpec(
        "current_password", "Mot de passe actuel", kind="password", autocomplete="current-password"
    ),
    FieldSpec(
        "new_password",
        "Nouveau mot de passe",
        kind="password",
        autocomplete="new-password",
        help="De 10 à 72 caractères, différent de l'actuel.",
    ),
)


def sign_in_form(values: Mapping[str, str], error: DomainError | None = None) -> FormView:
    return build_form(
        title="Se connecter",
        action="/sign-in",
        submit_label="Se connecter",
        specs=SIGN_IN_FIELDS,
        values=values,
        error=error,
    )


def password_form(*, forced: bool, error: DomainError | None = None) -> FormView:
    title = "Choisissez votre mot de passe" if forced else "Changer mon mot de passe"
    return build_form(
        title=title,
        action="/account/password",
        submit_label="Enregistrer",
        specs=PASSWORD_FIELDS,
        values={},
        error=error,
    )


@dataclass(frozen=True, slots=True)
class LinkSentView:
    title: str
    message: str


@dataclass(frozen=True, slots=True)
class LinkContinueView:
    """The page a link opens: one button holding the token, or a refusal with a new request."""

    title: str
    action: str
    token: str
    submit_label: str
    message: str
    request_form: FormView | None


def link_request_form(values: Mapping[str, str], error: DomainError | None = None) -> FormView:
    return build_form(
        title="Recevoir un lien de connexion",
        action="/sign-in/link/request",
        submit_label="Recevoir un lien",
        specs=LINK_FIELDS,
        values=values,
        error=error,
    )


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
        token="",
        submit_label="Continuer",
        message=error.message,
        request_form=link_request_form({}),
    )


def link_missing() -> LinkContinueView:
    return link_refused(DomainError(ErrorCode.UNAUTHENTICATED, NO_LINK_MESSAGE))
