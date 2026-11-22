from dataclasses import dataclass

from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.presenters.console import NavLink
from drlibre.interfaces.web.presenters.portal import (
    NOTIFICATIONS_URL,
    PROFILE_URL,
    notifications_label,
    portal_nav,
)
from drlibre.interfaces.web.presenters.workspace import workspace_nav

ROLE_LABELS = {Role.ADMIN: "Administration", Role.CLINICIAN: "Praticien", Role.PATIENT: "Patient"}
PASSWORD_URL = "/account/password"  # noqa: S105  # nosec B105


@dataclass(frozen=True, slots=True)
class AccountView:
    full_name: str
    first_name: str
    initials: str
    role_label: str
    links: tuple[NavLink, ...]


@dataclass(frozen=True, slots=True)
class BellView:
    url: str
    label: str
    unread: int
    current: bool


@dataclass(frozen=True, slots=True)
class ShellView:
    links: tuple[NavLink, ...]
    account: AccountView | None = None
    bell: BellView | None = None


def initials(full_name: str) -> str:
    """Up to two capitals, from the first and last words of the name."""
    words = full_name.split()
    picked = (words[0], words[-1]) if len(words) > 1 else tuple(words)
    return "".join(w[0].upper() for w in picked)


def shell_view(
    path: str,
    *,
    role: Role | None = None,
    full_name: str = "",
    has_password: bool = False,
    home_url: str = "",
    unread: int = 0,
) -> ShellView:
    """The header: section links on the left, notifications and the account menu on the right."""
    search = NavLink("/", "Rechercher", path == "/")
    if role is None:
        return ShellView((search,))
    if role is Role.CLINICIAN:
        sections = workspace_nav(path)
    elif role is Role.PATIENT:
        sections = portal_nav(path, home_url)
    else:
        sections = (NavLink(home_url, "Mon espace", path.startswith(home_url)),)
    links = (
        *(
            (NavLink(PROFILE_URL, "Profil", path.startswith(PROFILE_URL)),)
            if role is Role.PATIENT
            else ()
        ),
        *((NavLink(PASSWORD_URL, "Mot de passe", path == PASSWORD_URL),) if has_password else ()),
    )
    account = AccountView(
        full_name,
        full_name.split()[0] if full_name else "",
        initials(full_name),
        ROLE_LABELS[role],
        links,
    )
    bell = (
        BellView(
            NOTIFICATIONS_URL,
            notifications_label(unread),
            unread,
            path.startswith(NOTIFICATIONS_URL),
        )
        if role is Role.PATIENT
        else None
    )
    return ShellView((search, *sections), account, bell)
