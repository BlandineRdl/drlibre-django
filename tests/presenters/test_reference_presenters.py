import pytest

from drlibre.interfaces.web.presenters.reference import (
    Column,
    confirm_view,
    list_view,
    record_values,
    yes_no,
)
from drlibre.shared_kernel.dependents import Dependent, Dependents
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest
from tests import builders_organisation as build


def test_list_shows_text_status_total_and_keeps_the_search_in_page_links() -> None:
    hospitals = tuple(build.hospital(name=f"Hôpital {n}") for n in range(20))
    request = PageRequest(number=2, search="nord")

    view = list_view(
        title="Hôpitaux",
        base_url="/console/hospitals/",
        columns=(Column("Nom", lambda h: h.name), Column("Actif", lambda h: yes_no(h.active))),
        page=Page(hospitals, total=45, number=2),
        request=request,
        label=lambda h: h.label,
        done="deleted",
    )

    assert view.summary == "45 résultats · page 2 sur 3"
    assert view.previous_url == "/console/hospitals/?page=1&search=nord"
    assert view.next_url == "/console/hospitals/?page=3&search=nord"
    assert view.rows[0].cells == ("Hôpital 0", "Oui")
    assert view.rows[0].delete_url.endswith("/delete")
    assert view.status == "L'élément a été supprimé."


def test_record_values_feed_the_edit_form_as_text() -> None:
    room = build.room(Id(), active=False)

    values = record_values(room)

    assert values["equipment"] == "ECG, Tensiomètre"
    assert values["capacity"] == "2"
    assert values["active"] == ""
    assert values["department_id"] == str(room.department_id)


def test_refused_delete_lists_each_dependent_with_its_kind() -> None:
    dependents = Dependents((Dependent("department", Id(), "Cardiologie (CARD)"),))
    with pytest.raises(DomainError) as refused:
        dependents.refuse_if_any("Cet hôpital a encore des départements.")

    view = confirm_view(label="Nord (NORD)", action="/x", cancel_url="/y", error=refused.value)

    assert view.title == "Supprimer « Nord (NORD) » ?"
    assert view.refusal == "Cet hôpital a encore des départements."
    assert [(d.kind, d.label) for d in view.dependents] == [("Département", "Cardiologie (CARD)")]
