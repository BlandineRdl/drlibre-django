from drlibre.identity.application.ports.inbound import Role
from drlibre.interfaces.web.presenters.shell import initials, shell_view


def test_a_visitor_sees_search_and_no_account_menu() -> None:
    view = shell_view("/")

    assert [(link.label, link.current) for link in view.links] == [("Rechercher", True)]
    assert (view.account, view.bell) == (None, None)


def test_a_patient_reaches_profile_and_password_from_the_account_menu() -> None:
    view = shell_view(
        "/portal/profile",
        role=Role.PATIENT,
        full_name="Paul Patient",
        has_password=True,
        home_url="/portal/",
        unread=8,
    )

    assert [link.label for link in view.links] == [
        "Rechercher",
        "Mon espace",
        "Mes RDV",
        "Liste d'attente",
    ]
    assert not any(link.current for link in view.links)
    assert view.account is not None
    assert (view.account.initials, view.account.first_name, view.account.role_label) == (
        "PP",
        "Paul",
        "Patient",
    )
    assert [(link.label, link.current) for link in view.account.links] == [
        ("Profil", True),
        ("Mot de passe", False),
    ]
    assert view.bell is not None
    assert (view.bell.label, view.bell.unread) == ("Notifications (8 non lues)", 8)


def test_staff_have_no_bell_and_no_profile_link() -> None:
    view = shell_view("/console/", role=Role.ADMIN, full_name="Alice Admin", home_url="/console/")

    assert view.bell is None
    assert view.account is not None
    assert view.account.links == ()
    assert initials("Jean-Pierre de la Fontaine") == "JF"
