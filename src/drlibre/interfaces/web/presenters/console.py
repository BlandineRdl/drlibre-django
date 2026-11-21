from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NavLink:
    url: str
    label: str
    current: bool


_SECTIONS = (
    ("/console/", "Tableau de bord"),
    ("/console/hospitals/", "Hôpitaux"),
    ("/console/specialties/", "Spécialités"),
    ("/console/departments/", "Départements"),
    ("/console/rooms/", "Salles"),
    ("/console/appointment-types/", "Types de RDV"),
    ("/console/users/", "Utilisateurs"),
    ("/console/clinicians/", "Praticiens"),
    ("/console/appointments/", "Rendez-vous"),
    ("/console/waitlist/", "Liste d'attente"),
    ("/console/audit/", "Journal d'audit"),
    ("/console/settings/", "Réglages"),
)


def console_nav(path: str) -> tuple[NavLink, ...]:
    """The section whose prefix is longest marks the current page."""
    current = max((url for url, _ in _SECTIONS if path.startswith(url)), key=len, default="")
    return tuple(NavLink(url, label, url == current) for url, label in _SECTIONS)
