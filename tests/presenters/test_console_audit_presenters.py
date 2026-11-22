from datetime import UTC, datetime

from drlibre.audit.application.ports.inbound import AuditFilter, AuditRow
from drlibre.interfaces.web.presenters.audit_labels import action_label
from drlibre.interfaces.web.presenters.console_audit import actor_email, audit_page
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

TYPES = ("appointment", "user")
ACTOR = Id()


def filtered(**query: str) -> AuditFilter:
    return AuditFilter.from_query(
        actor_id=None,
        entity_type=query.get("entity_type"),
        start=query.get("from"),
        end=query.get("to"),
        time_zone="Europe/Paris",
        entity_types=TYPES,
    )


def test_rows_show_paris_time_actor_email_and_correlation_id() -> None:
    """Story journal : heure dans le fuseau nommé, acteur par email, vide sans acteur."""
    entity = Id()
    rows = (
        AuditRow(
            datetime(2026, 11, 20, 9, 5, tzinfo=UTC),
            ACTOR,
            "booking.appointment_cancelled",
            "appointment",
            entity,
            "corr-1",
        ),
        AuditRow(
            datetime(2026, 11, 20, 8, tzinfo=UTC),
            None,
            "booking.reminders_sent",
            "appointment",
            None,
            "corr-2",
        ),
    )

    view = audit_page(
        Page(rows, 2, 1),
        filtered(),
        email="",
        entity_types=TYPES,
        emails={ACTOR: "admin@drlibre.localhost"},
        time_zone="Europe/Paris",
    )

    assert view.rows == (
        (
            "20/11/2026 10:05:00",
            "admin@drlibre.localhost",
            "RDV annulé",
            f"Rendez-vous {entity}",
            "corr-1",
        ),
        ("20/11/2026 09:00:00", "", "Rappels envoyés", "Rendez-vous", "corr-2"),
    )
    assert view.zone_note == "Heures affichées dans le fuseau Europe/Paris."


def test_usable_filters_are_shown_again_and_kept_by_the_pagination() -> None:
    """Story journal : filtres acteur, entité et dates conservés d'une page à l'autre."""
    shown = filtered(entity_type="appointment", **{"from": "2026-11-01", "to": "2026-11-20"})

    view = audit_page(
        Page((), 45, 2),
        shown,
        email="admin@drlibre.localhost",
        entity_types=TYPES,
        emails={},
        time_zone="Europe/Paris",
    )

    assert (view.start, view.end, view.entity_type) == ("2026-11-01", "2026-11-20", "appointment")
    assert view.next_url == (
        "/console/audit/?page=3&actor=admin%40drlibre.localhost"
        "&entity_type=appointment&from=2026-11-01&to=2026-11-20"
    )
    assert view.previous_url.startswith("/console/audit/?page=1&")
    assert [(c.label, c.selected) for c in view.entity_choices] == [
        ("Rendez-vous", True),
        ("Utilisateur", False),
    ]


def test_an_unusable_filter_falls_back_to_the_default() -> None:
    """Story journal : un filtre inutilisable est ignoré, le journal reste complet."""
    shown = filtered(entity_type="unknown", **{"from": "hier", "to": "2026-13-01"})

    view = audit_page(
        Page((), 0, 1),
        shown,
        email=actor_email("pas un email"),
        entity_types=TYPES,
        emails={},
        time_zone="Europe/Paris",
    )

    assert (view.actor, view.entity_type, view.start, view.end) == ("", "", "", "")
    assert actor_email("  Admin@DrLibre.localhost ") == "admin@drlibre.localhost"


def test_a_reference_write_reads_as_its_entity_and_verb() -> None:
    """Story journal : l'action se lit en clair, même pour une écriture du référentiel."""
    assert action_label("room.created") == "Salle : créé"
    assert action_label("unknown.thing") == "unknown.thing"
