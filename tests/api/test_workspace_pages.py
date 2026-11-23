import dataclasses
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta

import pytest
from django.conf import settings
from django.test import Client

from drlibre.booking.domain.appointment import Appointment, AppointmentStatus
from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.bootstrap.container import use_container
from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.organisation.infrastructure.repositories import DjangoRooms
from tests import builders_organisation as build
from tests.builders import stored_session, stored_user
from tests.integration.bookable import SLOT_START, Bookable, bookable
from tests.markup import attributes

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]
COOKIE = settings.SESSION_COOKIE_NAME
MONDAY = "2026-11-23"
# Monday 10:00 in Paris, a free slot of the clinician.
TEN = "2026-11-23T09:00:00Z"


@dataclass
class Workspace:
    world: Bookable
    appointment: Appointment
    client: Client

    @property
    def base(self) -> str:
        return f"/workspace/appointments/{self.appointment.id}"

    def stored(self) -> Appointment:
        found = DjangoAppointments().get(self.appointment.id)
        assert found is not None
        return found


def named_patient(full_name: str) -> User:
    user = dataclasses.replace(stored_user(Role.PATIENT, password=None), full_name=full_name)
    DjangoUsers().save(user)
    return user


def clinician_client(world: Bookable, index: int = 0) -> Client:
    user = DjangoUsers().get(world.scene.clinicians[index].user_id)
    assert user is not None
    client = Client()
    client.cookies[COOKIE] = stored_session(user)
    return client


def book(world: Bookable, name: str, start: datetime = SLOT_START, index: int = 0) -> Appointment:
    return world.app().book_appointment.execute(
        patient_id=named_patient(name).id,
        appointment_type_id=world.scene.kind,
        clinician_id=world.scene.clinicians[index].id,
        start=start,
    )


@pytest.fixture
def workspace() -> Iterator[Workspace]:
    """Ana Martin booked with the first clinician on Monday 09:00 Paris, the clinician signed in."""
    with bookable() as world:
        use_container(world.app())
        booked = book(world, "Ana Martin")
        yield Workspace(world, booked, clinician_client(world))
        use_container(None)


def page(response: object) -> str:
    return response.content.decode()  # type: ignore[attr-defined]


def main(response: object) -> str:
    return page(response).split("<main", 1)[1].split("</main>", 1)[0]


def test_the_day_lists_own_appointments_by_hour_with_the_time_zone_named(
    workspace: Workspace,
) -> None:
    """Story agenda du jour : groupés par heure, patient, type, salle, statut ; fuseau nommé."""
    book(workspace.world, "Zoé Autre", SLOT_START + timedelta(hours=1), index=1)

    response = workspace.client.get(f"/workspace/?day={MONDAY}")

    body = main(response)
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    assert "Agenda du Lundi 23/11/2026" in body
    assert "Fuseau : Europe/Paris" in body
    assert '<h2 id="hour-1">09:00</h2>' in body
    assert "<strong>Ana Martin</strong>" in body
    assert "Statut : </span>Réservé" in body
    assert "Consultation · Salle : Salle 1" in body
    assert "Zoé Autre" not in body


def test_an_unusable_day_in_the_address_opens_today(workspace: Workspace) -> None:
    """Story agenda du jour : une date inutilisable dans l'adresse revient à aujourd'hui."""
    response = workspace.client.get("/workspace/?day=abc")

    assert response.status_code == 200
    assert "Agenda du Vendredi 20/11/2026" in main(response)
    assert 'aria-current="page">Aujourd&#x27;hui</a>' in page(response)


def test_the_day_offers_only_allowed_actions_and_a_check_in_comes_back_to_it(
    workspace: Workspace,
) -> None:
    """Story statut : seules les actions permises ; le changement revient avec un message."""
    before = main(workspace.client.get(f"/workspace/?day={MONDAY}"))

    done = workspace.client.post(f"{workspace.base}/check-in", {"from": "day"})
    after = main(workspace.client.get(done["Location"]))

    assert re.findall(r">(Arrivé|Absent|Terminé)</button>", before) == ["Arrivé", "Absent"]
    assert done["Location"] == f"/workspace/?day={MONDAY}&done=checked_in"
    assert '<p role="status" class="notice">Le patient est noté arrivé.</p>' in after
    assert re.findall(r">(Arrivé|Absent|Terminé)</button>", after) == ["Terminé"]
    assert workspace.stored().status is AppointmentStatus.CHECKED_IN


def test_a_forbidden_transition_is_explained_on_the_file(workspace: Workspace) -> None:
    """Story statut : une transition interdite renvoie invalid_transition avec le statut."""
    response = workspace.client.post(f"{workspace.base}/complete")

    assert response.status_code == 409
    assert "Statut actuel : Réservé." in main(response)


def test_the_week_shows_appointments_by_type_and_time_off_blocks(workspace: Workspace) -> None:
    """Story semaine : RDV actifs dans la couleur de leur type, absences en blocs, fuseau."""
    workspace.client.post(
        "/workspace/time-off/new", {"start": "2026-11-24T09:00", "end": "2026-11-24T10:00"}
    )
    cancelled = book(workspace.world, "Léo Roy", SLOT_START + timedelta(hours=1))
    workspace.world.app().cancel_appointment.execute(
        appointment_id=cancelled.id, actor_id=cancelled.patient_id, reason="Empêchement"
    )

    response = workspace.client.get(f"/workspace/calendar?week={MONDAY}")

    body = main(response)
    assert response.status_code == 200
    assert "Fuseau : Europe/Paris" in body
    assert (f'class="appointment hue-5"><a href="{workspace.base}">Consultation</a>') in body
    assert body.count(">Consultation</a>") == 1
    assert body.count('class="time-off">Absence</td>') == 2


def test_the_file_shows_the_facts_notes_week_strip_and_history(workspace: Workspace) -> None:
    """Story fiche : patient, heure, type, salle, motif, statut, historique ; no-store."""
    response = workspace.client.get(workspace.base)

    body = main(response)
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    assert "<dt>Patient</dt><dd>Ana Martin</dd>" in body
    assert "<dt>Horaire</dt><dd>Lundi 23/11/2026, 09:00-09:30</dd>" in body
    assert "<dt>Salle</dt><dd>Salle 1</dd>" in body
    assert 'id="field-clinical_notes"' in body
    assert f'value="{TEN}"' in body
    assert "<td>RDV réservé</td><td>Patient</td>" in body


def test_notes_are_saved_apart_and_refused_beyond_the_limit(workspace: Workspace) -> None:
    """Story notes : enregistrées depuis la fiche, à part ; au-delà de 5000, invalid_input."""
    saved = workspace.client.post(f"{workspace.base}/notes", {"clinical_notes": "Tension 12/8"})
    refused = workspace.client.post(f"{workspace.base}/notes", {"clinical_notes": "x" * 5001})

    assert saved["Location"] == f"{workspace.base}?done=notes"
    assert workspace.stored().clinical_notes == "Tension 12/8"
    assert refused.status_code == 400
    assert attributes(page(refused), "field-clinical_notes")["aria-invalid"] == "true"
    assert "Notes cliniques enregistrées" in main(workspace.client.get(workspace.base))


def test_cancelling_needs_a_reason_then_records_it_and_grows_the_history(
    workspace: Workspace,
) -> None:
    """Story annule : motif obligatoire ; l'heure et le motif sont enregistrés sur le RDV."""
    missing = workspace.client.post(f"{workspace.base}/cancel", {"reason": " "})
    done = workspace.client.post(f"{workspace.base}/cancel", {"reason": "Praticien absent"})
    file = main(workspace.client.get(done["Location"]))

    assert missing.status_code == 400
    assert attributes(page(missing), "field-reason")["aria-invalid"] == "true"
    assert done["Location"] == f"{workspace.base}?done=cancelled"
    assert workspace.stored().cancellation_reason == "Praticien absent"
    assert "<td>RDV annulé</td><td>Praticien</td>" in file
    assert f'action="{workspace.base}/cancel"' not in file


def test_the_cancel_form_of_an_appointment_no_longer_cancellable_leads_back_to_it(
    workspace: Workspace,
) -> None:
    """Story annule : depuis un statut définitif, la fiche ne propose plus l'annulation."""
    workspace.client.post(f"{workspace.base}/cancel", {"reason": "Praticien absent"})
    again = workspace.client.get(f"{workspace.base}/cancel")

    assert (again.status_code, again["Location"]) == (302, workspace.base)


def test_rescheduling_from_the_strip_moves_it_and_a_busy_start_is_refused_inline(
    workspace: Workspace,
) -> None:
    """Story déplace : bandeau de créneaux libres ; un début non libre donne rule_violation."""
    refused = workspace.client.post(
        f"{workspace.base}/reschedule", {"start": "2026-11-23T12:00:00Z", "week": MONDAY}
    )
    done = workspace.client.post(f"{workspace.base}/reschedule", {"start": TEN, "week": MONDAY})

    assert refused.status_code == 422
    assert "ce créneau n&#x27;est pas libre" in main(refused)
    assert done["Location"] == f"{workspace.base}?done=moved"
    assert workspace.stored().start == datetime.fromisoformat(TEN)


def test_another_clinicians_appointment_shows_not_your_appointment_and_none_of_its_data(
    workspace: Workspace,
) -> None:
    """Story fiche : le RDV d'un autre praticien affiche « Not your appointment »."""
    other = clinician_client(workspace.world, index=1)

    response = other.get(workspace.base)
    action = other.post(f"{workspace.base}/check-in")

    body = main(response)
    assert (response.status_code, action.status_code) == (403, 403)
    assert '<p lang="en">Not your appointment</p>' in body
    assert "Ana Martin" not in body
    assert workspace.stored().status is AppointmentStatus.BOOKED


def test_an_unknown_appointment_is_not_found(workspace: Workspace) -> None:
    """Story fiche : un RDV inexistant donne not_found."""
    response = workspace.client.get("/workspace/appointments/00000000-0000-4000-8000-000000000000")

    assert response.status_code == 404


def test_the_patients_list_holds_own_patients_found_by_name(workspace: Workspace) -> None:
    """Story patients : ses patients seuls, avec téléphone et visites ; recherche par nom."""
    book(workspace.world, "Léo Roy", SLOT_START + timedelta(hours=1))
    book(workspace.world, "Zoé Autre", SLOT_START + timedelta(hours=2), index=1)

    listing = workspace.client.get("/workspace/patients")
    found = main(workspace.client.get("/workspace/patients?q=mar"))

    body = main(listing)
    assert listing["Cache-Control"] == "no-store"
    assert '<th scope="row">Ana Martin</th>' in body
    assert '<th scope="row">Léo Roy</th>' in body
    assert "Zoé Autre" not in body
    assert "<td>23/11/2026 09:00</td>" in body
    assert "Ana Martin" in found
    assert "Léo Roy" not in found


def test_a_name_search_without_match_offers_to_show_every_patient(workspace: Workspace) -> None:
    """Story patients : une recherche sans résultat le dit et propose de tout afficher."""
    body = main(workspace.client.get("/workspace/patients?q=zz"))

    assert "Aucun patient ne correspond à « zz »." in body
    assert '<a href="/workspace/patients">Afficher tous mes patients</a>' in body


def test_the_rooms_timeline_names_only_own_patients_and_skips_inactive_rooms(
    workspace: Workspace,
) -> None:
    """Story salles : salles actives, ses patients nommés, les autres « Occupied », fuseau."""
    book(workspace.world, "Zoé Autre", SLOT_START + timedelta(hours=1), index=1)
    room = build.room(workspace.world.scene.department, name="Salle fermée", active=False)
    DjangoRooms().save(room)

    response = workspace.client.get(f"/workspace/rooms?day={MONDAY}")

    body = main(response)
    assert response.status_code == 200
    assert "Fuseau : Europe/Paris" in body
    assert '<th scope="row">Salle 1</th>' in body
    assert "Salle fermée" not in body
    assert '<td class="busy">Ana Martin</td>' in body
    assert '<td class="busy"><span lang="en">Occupied</span></td>' in body
    assert "Zoé Autre" not in page(response)
