import pytest

from drlibre.booking.domain.waitlist import WaitlistStatus
from drlibre.identity.domain.user import Role
from tests.api.waitlist_scene import waitlist_scene
from tests.builders import stored_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]


def page(response: object) -> str:
    return response.content.decode()  # type: ignore[attr-defined]


def test_every_waitlist_page_renders_for_a_passwordless_patient_and_an_admin() -> None:
    """§8, §10 : les pages de liste d'attente s'affichent pour leur rôle, 403 pour les autres."""
    with waitlist_scene() as scene:
        patient, staff = scene.client(), scene.client(stored_user(Role.ADMIN))

        portal = patient.get("/portal/waitlist")
        listing = staff.get("/console/waitlist/")
        new = staff.get("/console/waitlist/new")
        refused = (patient.get("/console/waitlist/"), staff.get("/portal/waitlist"))

        assert (portal.status_code, listing.status_code, new.status_code) == (200, 200, 200)
        assert portal["Cache-Control"] == "no-store"
        assert 'href="/portal/waitlist">Liste d\'attente</a>' in page(portal)
        assert [r.status_code for r in refused] == [403, 403]


def test_the_patient_joins_from_the_form_and_sees_the_entry_waiting() -> None:
    """Story « le patient s'inscrit » : type, praticien facultatif, fenêtre ; entrée `WAITING`."""
    with waitlist_scene() as scene:
        client = scene.client(stored_user(Role.PATIENT, password=None))
        form = page(client.get("/portal/waitlist"))

        done = client.post(
            "/portal/waitlist",
            {
                "appointment_type_id": str(scene.world.scene.kind),
                "clinician_id": "",
                "from_date": "2026-11-23",
                "to_date": "2026-11-27",
            },
        )
        listed = page(client.get(done["Location"]))

        assert f'value="{scene.world.scene.kind}"' in form
        assert f'value="{scene.world.clinician}"' in form
        assert done["Location"] == "/portal/waitlist?done=joined"
        assert "Inscription enregistrée." in listed
        assert "Statut : En attente" in listed
        assert "Du 23/11/2026 au 27/11/2026" in listed


def test_a_refused_join_shows_the_form_again_with_its_field_errors() -> None:
    """Story « le patient s'inscrit » : une fenêtre inversée ou une date manquante est refusée."""
    with waitlist_scene() as scene:
        client = scene.client()
        body = {"appointment_type_id": str(scene.world.scene.kind), "from_date": "2026-11-27"}

        inverted = client.post("/portal/waitlist", {**body, "to_date": "2026-11-23"})
        missing = client.post("/portal/waitlist", body)

        assert inverted.status_code == 400
        assert 'href="#field-to_date"' in page(inverted)
        assert missing.status_code == 400
        assert "Saisissez une date." in page(missing)


def test_an_offered_entry_shows_its_time_and_accepting_books_it() -> None:
    """Story « le patient accepte » : heure et « Accepter », RDV et entrée `BOOKED`."""
    with waitlist_scene() as scene:
        client = scene.client()
        card = page(client.get("/portal/waitlist"))

        done = client.post(f"/portal/waitlist/{scene.entry.id}/accept")
        appointments = page(client.get(done["Location"]))
        again = client.post(f"/portal/waitlist/{scene.entry.id}/accept")

        assert "Statut : Créneau proposé" in card
        assert "Proposé : lun. 23/11/2026 09:00, fuseau Europe/Paris" in card
        assert f'action="/portal/waitlist/{scene.entry.id}/accept"' in card
        assert done["Location"] == "/portal/appointments?done=booked"
        assert "Le créneau proposé est réservé." in appointments
        assert "lun. 23/11/2026 de 09:00 à 09:30" in appointments
        assert scene.stored().status is WaitlistStatus.BOOKED
        assert again.status_code == 409
        assert "Statut actuel : RDV obtenu." in page(again)


def test_the_admin_lists_entries_by_status_and_falls_back_on_a_bad_filter() -> None:
    """Story « l'admin suit la liste » : par statut ; un filtre inutilisable revient à tous."""
    with waitlist_scene() as scene:
        staff = scene.client(stored_user(Role.ADMIN))

        offered = page(staff.get("/console/waitlist/?status=OFFERED"))
        waiting = page(staff.get("/console/waitlist/?status=WAITING"))
        bogus = staff.get("/console/waitlist/?status=bogus&page=x")

        assert "Accepter pour le patient" in offered
        assert "1 résultat · page 1 sur 1" in offered
        assert "Aucune entrée pour ce statut." in waiting
        assert bogus.status_code == 200
        assert "1 résultat · page 1 sur 1" in page(bogus)


def test_the_admin_accepts_an_offer_for_the_patient_from_the_list() -> None:
    """Story « l'admin accepte » : RDV `BOOKED` pour le patient, entrée `BOOKED`."""
    with waitlist_scene() as scene:
        staff = scene.client(stored_user(Role.ADMIN))

        done = staff.post(f"/console/waitlist/{scene.entry.id}/accept", {"status": "OFFERED"})

        assert done["Location"] == "/console/waitlist/?done=booked"
        assert "Le rendez-vous est réservé pour le patient." in page(staff.get(done["Location"]))
        assert scene.stored().status is WaitlistStatus.BOOKED


def test_the_admin_offers_a_cancelled_slot_then_finds_none_left() -> None:
    """Story « l'admin propose » : entrée `OFFERED` ; sans créneau, refus affiché."""
    with waitlist_scene(offered=False) as scene:
        staff = scene.client(stored_user(Role.ADMIN))
        listed = page(staff.get("/console/waitlist/"))

        done = staff.post(f"/console/waitlist/{scene.entry.id}/offer")
        offered = scene.stored()
        refused = staff.post(f"/console/waitlist/{scene.entry.id}/offer")

        assert f'action="/console/waitlist/{scene.entry.id}/offer"' in listed
        assert done["Location"] == "/console/waitlist/?done=offered"
        assert offered.status is WaitlistStatus.OFFERED
        assert offered.offered_appointment_id == scene.freed.id
        assert refused.status_code == 409
        assert "Statut actuel : Créneau proposé." in page(refused)


def test_the_admin_adds_a_patient_by_email_from_the_console() -> None:
    """Story « l'admin inscrit un patient » : patient nommé par son email, entrée listée."""
    with waitlist_scene() as scene:
        staff = scene.client(stored_user(Role.ADMIN))
        other = stored_user(Role.PATIENT, password=None)
        body = {
            "patient_email": other.email.value,
            "appointment_type_id": str(scene.world.scene.kind),
            "from_date": "2026-11-23",
            "to_date": "2026-11-27",
        }

        done = staff.post("/console/waitlist/new", body)
        unknown = staff.post("/console/waitlist/new", {**body, "patient_email": "x@example.org"})

        assert done["Location"] == "/console/waitlist/?done=added"
        assert "2 résultats" in page(staff.get("/console/waitlist/"))
        assert unknown.status_code == 404
        assert "Patient introuvable." in page(unknown)
