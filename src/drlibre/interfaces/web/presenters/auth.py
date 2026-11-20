from collections.abc import Mapping

from drlibre.interfaces.web.presenters.forms import FieldSpec, FormView, build_form
from drlibre.shared_kernel.errors import DomainError

SIGN_IN_FIELDS = (
    FieldSpec("email", "Email", kind="email", autocomplete="username"),
    FieldSpec("password", "Mot de passe", kind="password", autocomplete="current-password"),
)
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
