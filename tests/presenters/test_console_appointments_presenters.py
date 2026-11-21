from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlsplit

import pytest

from drlibre.booking.application.ports.inbound import (
    AdminAppointmentFilter,
    AdminAppointmentRow,
    AppointmentStatus,
    ExportRow,
    Source,
)
from drlibre.interfaces.web.presenters.console_appointments import (
    CSV_HEADERS,
    AppointmentsListView,
    appointment_filter,
    csv_cell,
    csv_rows,
    file_page,
    list_page,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page
from tests.builders_booking import existing_appointment
from tests.presenters.test_workspace_presenters import entry, file

START = datetime(2026, 11, 23, 8, tzinfo=UTC)


def row(time_zone: str = "Europe/Paris") -> AdminAppointmentRow:
    a = existing_appointment(
        patient_id=Id(), clinician_id=Id(), start=START, end=START + timedelta(minutes=30)
    )
    return AdminAppointmentRow(
        appointment=a,
        patient_name="Ana Martin",
        clinician_name="Dr Petit",
        department="Cardiologie",
        appointment_type="Consultation",
        room=None,
        hospital_name="Hôpital Nord",
        time_zone=time_zone,
    )


def listed(page: Page[AdminAppointmentRow], shown: AdminAppointmentFilter) -> AppointmentsListView:
    return list_page(page, shown, departments=(), clinicians=())


def test_unusable_filter_values_fall_back_to_no_filter() -> None:
    """Plan E7 : une valeur de filtre inutilisable redevient le défaut."""
    shown = appointment_filter(
        {"from": "hier", "to": "2026-13-01", "department": "x", "status": "CONFIRMED"}
    )

    assert shown == AdminAppointmentFilter()


def test_pagination_and_export_keep_the_filters() -> None:
    """Story « l'admin liste les RDV » : les liens de page et l'export gardent les filtres."""
    shown = appointment_filter({"from": "2026-11-01", "status": "BOOKED", "source": "nope"})
    page = Page(tuple(row() for _ in range(20)), 45, 2)

    view = listed(page, shown)

    next_query = parse_qs(urlsplit(view.next_url).query)
    assert next_query == {"from": ["2026-11-01"], "status": ["BOOKED"], "page": ["3"]}
    assert parse_qs(urlsplit(view.previous_url).query)["page"] == ["1"]
    assert parse_qs(urlsplit(view.export_url).query) == {
        "from": ["2026-11-01"],
        "status": ["BOOKED"],
    }
    assert view.summary == "45 résultats · page 2 sur 3"
    assert [c.value for c in view.filters.statuses if c.selected] == ["BOOKED"]


def test_each_row_shows_its_start_in_its_hospitals_named_time_zone() -> None:
    """Story « l'admin liste les RDV » : heure dans le fuseau de l'hôpital du RDV, nommé."""
    view = listed(
        Page((row("Europe/Paris"), row("America/Cayenne")), 2, 1), AdminAppointmentFilter()
    )

    assert [r.cells[0] for r in view.rows] == [
        "23/11/2026 09:00 (Europe/Paris)",
        "23/11/2026 05:00 (America/Cayenne)",
    ]
    assert view.rows[0].cells[5:] == ("Réservé", "En ligne", "—")


@pytest.mark.parametrize("start", ["=", "+", "-", "@", "\t", "\r"])
def test_a_csv_cell_that_could_run_as_a_formula_is_prefixed(start: str) -> None:
    """Spec §13 : une cellule commençant par = + - @ est préfixée d'une apostrophe."""
    assert csv_cell(f"{start}SUM(A1)") == f"'{start}SUM(A1)"


def test_a_plain_csv_cell_is_left_as_is() -> None:
    """Spec §13 : les autres cellules restent telles quelles."""
    assert csv_cell("BOOKED") == "BOOKED"


def test_the_csv_holds_ids_utc_instants_and_codes_only() -> None:
    """Spec §13 : colonnes d'ids, instants ISO 8601 UTC, sans nom ni texte libre."""
    exported = ExportRow(
        id=Id(),
        start=datetime(2026, 11, 23, 9, tzinfo=UTC),
        end=datetime(2026, 11, 23, 9, 30, tzinfo=UTC),
        status=AppointmentStatus.CANCELLED,
        source=Source.STAFF,
        patient_id=Id(),
        clinician_id=Id(),
        department_id=Id(),
        appointment_type_id=Id(),
        room_id=None,
    )

    header, line = list(csv_rows((exported,)))

    assert header == CSV_HEADERS
    assert line[:5] == (
        str(exported.id),
        "2026-11-23T09:00:00+00:00",
        "2026-11-23T09:30:00+00:00",
        "CANCELLED",
        "STAFF",
    )
    assert line[-1] == ""


def test_the_file_offers_only_the_actions_the_status_allows() -> None:
    """Story « l'admin annule ou change le statut » : seules les actions permises."""
    booked = file_page(file(entry()), week=None)
    completed = file_page(file(entry(status=AppointmentStatus.COMPLETED)), week=None)

    assert [b.label for b in booked.buttons] == ["Arrivé", "Absent"]
    assert booked.cancel_url.endswith("/cancel")
    assert booked.cancel_url.startswith("/console/appointments/")
    assert (completed.buttons, completed.cancel_url, completed.strip) == ((), "", None)


def test_the_file_shows_its_source_and_no_notes() -> None:
    """Règle §3.1 : la fiche admin n'affiche jamais les notes cliniques."""
    view = file_page(file(entry()), week=None)

    assert ("Source", "En ligne") in [(f.label, f.value) for f in view.facts]
    assert not hasattr(view, "notes")
