from dataclasses import dataclass

import pytest

from drlibre.booking.application.ports.outbound import BookingDirectory
from drlibre.booking.infrastructure.directory import OrganisationBookingDirectory
from drlibre.identity.domain.user import Role
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.organisation.infrastructure.queries import DjangoReferenceQueries
from drlibre.shared_kernel.ids import Id
from tests.builders import stored_user
from tests.builders_scheduling import stored_department, stored_profile
from tests.fakes.booking import FixedBookingDirectory

REAL = [pytest.mark.integration, pytest.mark.django_db]


@dataclass
class Known:
    """A clinician user with their profile, and a staff user holding none."""

    directory: BookingDirectory
    clinician_user: Id
    profile: Id
    profileless_user: Id


def fake() -> Known:
    directory = FixedBookingDirectory()
    user, profile = Id(), Id()
    directory.profiles_of_users[user] = profile
    return Known(directory, user, profile, Id())


def real() -> Known:
    user = stored_user(Role.CLINICIAN)
    profileless = stored_user(Role.CLINICIAN)
    profile = stored_profile(stored_department(), user_id=user.id)
    directory = OrganisationBookingDirectory(
        queries=DjangoReferenceQueries(), staff=DjangoUserQueries()
    )
    return Known(directory, user.id, profile.id, profileless.id)


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="django", marks=REAL)]
)
def known(request: pytest.FixtureRequest) -> Known:
    return fake() if request.param == "fake" else real()


def test_the_signed_in_clinician_is_resolved_to_their_own_profile(known: Known) -> None:
    """Spec §9 : le praticien n'agit que sur les RDV de son propre profil."""
    assert known.directory.clinician_of_user(known.clinician_user) == known.profile


def test_a_user_without_profile_has_no_clinician(known: Known) -> None:
    """Story statut : sans profil praticien, l'action est refusée."""
    assert known.directory.clinician_of_user(known.profileless_user) is None
    assert known.directory.clinician_of_user(Id()) is None
