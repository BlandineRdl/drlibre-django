import dataclasses
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import pytest

from drlibre.booking.infrastructure.repositories import DjangoAppointments
from drlibre.identity.domain.user import Role, User
from drlibre.identity.infrastructure.repositories import DjangoUsers
from drlibre.interop.application.ports.inbound import (
    Paging,
    PatientFilter,
    PatientQueries,
    Reader,
    ReaderKind,
)
from drlibre.interop.infrastructure.sql_patients import SqlPatientQueries
from drlibre.shared_kernel.ids import Id
from tests.builders import unique_email
from tests.builders_booking import existing_appointment, patient_user, stored_scene
from tests.fakes.world import FakeWorld

REAL = [pytest.mark.integration, pytest.mark.django_db]
_SEEN = datetime(2026, 1, 5, 9, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Scene:
    anne: User
    bruno: User
    clinician: Reader
    admin: Reader

    def patient(self, user: User) -> Reader:
        return Reader(ReaderKind.PATIENT, user.id)


def _person(name: str, phone: str, born: date, role: Role = Role.PATIENT) -> User:
    user = patient_user(Id(), email=unique_email("p"), role=role)
    return dataclasses.replace(user, full_name=name, phone=phone, birth_date=born)


def _scene(
    save_user: Callable[[User], None], add_seen: Callable[[Id], None], clinician_profile: Id
) -> Scene:
    anne = _person("Anne Durand", "0611111111", date(1980, 3, 4))
    bruno = _person("Bruno Petit", "0622222222", date(1990, 5, 1))
    admin = _person("Admin", "0600000000", date(1970, 1, 1), Role.ADMIN)
    for user in (anne, bruno, admin):
        save_user(user)
    add_seen(anne.id)
    clinician = Reader(ReaderKind.CLINICIAN, Id(), clinician_profile)
    return Scene(anne, bruno, clinician, Reader(ReaderKind.ADMIN, admin.id))


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="sql", marks=REAL)]
)
def patients(request: pytest.FixtureRequest) -> tuple[PatientQueries, Scene]:
    if request.param == "fake":
        world = FakeWorld()
        profile, kind = Id(), Id()
        port = world.app.patient_queries
        save, store = world.users.save, world.booking_appointments.add
    else:
        stored = stored_scene()
        profile, kind = stored.clinicians[0].id, stored.kind
        port, save, store = SqlPatientQueries(), DjangoUsers().save, DjangoAppointments().add

    def seen(patient_id: Id) -> None:
        end = _SEEN + timedelta(minutes=30)
        store(
            existing_appointment(
                patient_id=patient_id,
                clinician_id=profile,
                start=_SEEN,
                end=end,
                appointment_type_id=kind,
            )
        )

    return port, _scene(save, seen, profile)


def names(port: PatientQueries, reader: Reader, criteria: PatientFilter | None = None) -> list[str]:
    found = port.patients(criteria or PatientFilter(), reader)
    return [r.full_name for r in found.items]


def test_a_patient_sees_only_themselves(patients: tuple[PatientQueries, Scene]) -> None:
    """Story jeton: `Patient` is readable by the patient themselves."""
    port, scene = patients

    assert names(port, scene.patient(scene.anne)) == ["Anne Durand"]


def test_a_clinician_sees_the_patients_they_have_an_appointment_with(
    patients: tuple[PatientQueries, Scene],
) -> None:
    """Story jeton: a clinician reads their own patients, as on their patients page."""
    port, scene = patients

    assert names(port, scene.clinician) == ["Anne Durand"]


def test_the_admin_sees_every_patient_but_no_staff(patients: tuple[PatientQueries, Scene]) -> None:
    port, scene = patients

    assert names(port, scene.admin) == ["Anne Durand", "Bruno Petit"]
    assert names(port, Reader.anonymous()) == []


def test_patients_are_searched_by_name_email_phone_and_birth_date(
    patients: tuple[PatientQueries, Scene],
) -> None:
    port, scene = patients

    assert names(port, scene.admin, PatientFilter(name="petit")) == ["Bruno Petit"]
    assert names(port, scene.admin, PatientFilter(email=scene.anne.email.value.upper())) == [
        "Anne Durand"
    ]
    assert names(port, scene.admin, PatientFilter(phone="0622222222")) == ["Bruno Petit"]
    assert names(port, scene.admin, PatientFilter(birth_date=date(1980, 3, 4))) == ["Anne Durand"]


def test_a_page_counts_every_match_and_reads_in_reverse(
    patients: tuple[PatientQueries, Scene],
) -> None:
    port, scene = patients

    page = port.patients(PatientFilter(), scene.admin, Paging(count=1, descending=True))

    assert [r.full_name for r in page.items] == ["Bruno Petit"]
    assert page.total == 2


def test_a_row_carries_the_fields_of_the_patient_and_its_last_update(
    patients: tuple[PatientQueries, Scene],
) -> None:
    port, scene = patients

    (row,) = port.patients(PatientFilter(ids=(scene.anne.id,)), scene.admin).items

    assert (row.email, row.phone, row.birth_date, row.active) == (
        scene.anne.email.value,
        "0611111111",
        date(1980, 3, 4),
        True,
    )
    assert row.updated_at == scene.anne.updated_at


def test_a_hidden_patient_exists_and_a_staff_user_is_no_patient(
    patients: tuple[PatientQueries, Scene],
) -> None:
    """Story jeton: another existing record is `forbidden`, an absent one `not_found`."""
    port, scene = patients

    assert port.exists(scene.bruno.id)
    assert not port.exists(scene.admin.user_id or Id())
    assert not port.exists(Id())


def test_an_email_is_matched_whole(patients: tuple[PatientQueries, Scene]) -> None:
    port, scene = patients

    assert names(port, scene.admin, PatientFilter(email="anne")) == []
