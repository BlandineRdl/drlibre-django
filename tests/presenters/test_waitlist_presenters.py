import dataclasses
from datetime import UTC, datetime, timedelta

import pytest

from drlibre.booking.application.ports.inbound import WaitlistRow, WaitlistStatus
from drlibre.booking.domain.waitlist import WaitlistEntry
from drlibre.interfaces.web.presenters.waitlist import (
    console_list,
    entry_card,
    join_input,
    refusal_text,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)
# Monday 09:00 in Paris.
START = datetime(2026, 11, 23, 8, tzinfo=UTC)
ZONE = "Europe/Paris"


def row(status: WaitlistStatus, offered_start: datetime | None = START) -> WaitlistRow:
    entry = WaitlistEntry(
        id=Id(),
        patient_id=Id(),
        appointment_type_id=Id(),
        clinician_id=None,
        earliest=datetime(2026, 11, 22, 23, tzinfo=UTC),
        latest=datetime(2026, 11, 27, 23, tzinfo=UTC),
        status=status,
        created_at=NOW,
        offered_appointment_id=Id() if status is WaitlistStatus.OFFERED else None,
    )
    return WaitlistRow(
        entry=entry,
        patient_name="Ana Martin",
        appointment_type="Consultation",
        hospital_name="Hôpital Nord",
        time_zone=ZONE,
        clinician_name=None,
        offered_start=offered_start if status is WaitlistStatus.OFFERED else None,
    )


@pytest.mark.parametrize(
    ("status", "label"),
    [
        (WaitlistStatus.WAITING, "En attente"),
        (WaitlistStatus.OFFERED, "Créneau proposé"),
        (WaitlistStatus.BOOKED, "RDV obtenu"),
        (WaitlistStatus.EXPIRED, "Expirée"),
    ],
)
def test_each_status_shows_its_label_and_the_window_as_the_chosen_dates(
    status: WaitlistStatus, label: str
) -> None:
    """Story « le patient s'inscrit » : le patient voit ses entrées avec leur statut."""
    card = entry_card(row(status), NOW)

    assert card.status == f"Statut : {label}"
    assert "Du 23/11/2026 au 27/11/2026" in card.lines


def test_an_offered_entry_shows_its_time_with_the_zone_and_accept_only_when_allowed() -> None:
    """Story « un créneau annulé est proposé » : heure proposée et bouton « Accepter »."""
    offered = entry_card(row(WaitlistStatus.OFFERED), NOW)
    too_late = entry_card(row(WaitlistStatus.OFFERED), START - timedelta(minutes=30))
    waiting = entry_card(row(WaitlistStatus.WAITING), NOW)

    assert offered.offered == "Proposé : lun. 23/11/2026 09:00, fuseau Europe/Paris"
    assert offered.accept_url.endswith("/accept")
    assert (too_late.offered != "", too_late.accept_url) == (True, "")
    assert (waiting.offered, waiting.accept_url) == ("", "")


def test_the_admin_list_offers_per_status_and_keeps_the_filter_in_its_pages() -> None:
    """Story « l'admin suit la liste » : filtrée par statut, par pages de 20 avec le total."""
    rows = (row(WaitlistStatus.WAITING), row(WaitlistStatus.OFFERED), row(WaitlistStatus.BOOKED))
    view = console_list(Page(rows, 41, 2), "WAITING", NOW)
    waiting, offered, booked = view.rows

    assert view.summary == "41 résultats · page 2 sur 3"
    assert view.previous_url == "/console/waitlist/?page=1&status=WAITING"
    assert view.next_url == "/console/waitlist/?page=3&status=WAITING"
    assert (bool(waiting.offer_url), bool(waiting.accept_url)) == (True, False)
    assert (bool(offered.offer_url), bool(offered.accept_url)) == (False, True)
    assert (booked.offer_url, booked.accept_url) == ("", "")
    assert all("fuseau Europe/Paris" in r.cells[0] for r in view.rows)
    assert offered.cells[6] == "lun. 23/11/2026 09:00, fuseau Europe/Paris"


def test_an_unusable_status_filter_falls_back_to_every_status() -> None:
    """Story « l'admin suit la liste » : un filtre inutilisable revient à la valeur par défaut."""
    view = console_list(Page((), 0, 1), "bogus", NOW)

    assert view.status == ""
    assert not any(c.selected for c in view.status_choices)
    assert view.next_url == ""


def test_an_offer_whose_start_has_passed_is_not_accepted_from_the_console() -> None:
    """Règle §10 : l'admin accepte une entrée proposée dont le début est encore à venir."""
    started = dataclasses.replace(row(WaitlistStatus.OFFERED), offered_start=NOW)

    (shown,) = console_list(Page((started,), 1, 1), "", NOW).rows

    assert shown.accept_url == ""


def test_refusals_name_the_entry_status_and_the_broken_rules() -> None:
    """Story « le patient accepte » : sinon `rule_violation` avec les règles violées."""
    transition = DomainError(ErrorCode.INVALID_TRANSITION, "Refusé.", {"status": "BOOKED"})
    rules = DomainError(ErrorCode.RULE_VIOLATION, "Refusé.", {"rules": ["too_many_open_bookings"]})

    assert refusal_text(transition) == "Refusé. Statut actuel : RDV obtenu."
    assert refusal_text(rules) == "Refusé. Vous avez déjà 3 réservations en ligne."


def test_the_join_form_names_each_unusable_field() -> None:
    """Story « le patient s'inscrit » : type, praticien facultatif et fenêtre de dates."""
    with pytest.raises(DomainError) as refused:
        join_input({"appointment_type_id": "x", "clinician_id": "y", "from_date": ""})

    fields = [f["field"] for f in refused.value.details["fields"]]
    assert fields == ["appointment_type_id", "clinician_id", "from_date", "to_date"]
