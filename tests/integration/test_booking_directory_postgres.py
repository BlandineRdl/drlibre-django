import pytest

from drlibre.booking.infrastructure.directory import OrganisationBookingDirectory
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.organisation.infrastructure.queries import DjangoReferenceQueries
from drlibre.shared_kernel.ids import Id
from tests.builders_booking import stored_scene

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_an_appointment_type_carries_the_time_zone_of_its_hospital() -> None:
    """Décision du plan : la fenêtre d'attente se lit dans le fuseau de l'hôpital du type."""
    scene = stored_scene()
    directory = OrganisationBookingDirectory(
        queries=DjangoReferenceQueries(), staff=DjangoUserQueries()
    )

    kind = directory.appointment_type(scene.kind)

    assert kind is not None
    assert kind.time_zone == "Europe/Paris"
    assert directory.appointment_type(Id()) is None
