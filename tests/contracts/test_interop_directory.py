from datetime import date
from typing import Any

import pytest

from drlibre.interop.application.ports.inbound import DirectoryQueries, Reader, ReaderKind
from drlibre.interop.domain.filters import (
    LocationFilter,
    LocationKind,
    Near,
    OrganizationFilter,
    OrganizationKind,
    Paging,
    PractitionerFilter,
    RoleFilter,
    ScheduleFilter,
    ServiceFilter,
    SpecialtyFilter,
)
from drlibre.interop.domain.rows import DepartmentRow, HospitalRow, RoomRow
from drlibre.interop.infrastructure.sql_directory import SqlDirectoryQueries
from drlibre.shared_kernel.pagination import Page
from tests.fakes.world import FakeWorld
from tests.fhir.directory_scene import Directory, a_directory, django_repos, world_repos

REAL = [pytest.mark.integration, pytest.mark.django_db]
VISITOR = Reader.anonymous()


@pytest.fixture(
    params=[pytest.param("fake", id="in-memory"), pytest.param("real", id="sql", marks=REAL)]
)
def directory(request: pytest.FixtureRequest) -> tuple[DirectoryQueries, Directory]:
    if request.param == "fake":
        world = FakeWorld()
        return world.directory_queries, a_directory(world_repos(world))
    return SqlDirectoryQueries(), a_directory(django_repos())


def clinician(scene: Directory) -> Reader:
    return Reader(ReaderKind.CLINICIAN, scene.clinician.id, scene.profile.id)


def admin(scene: Directory) -> Reader:
    return Reader(ReaderKind.ADMIN, scene.admin.id)


def names(rows: Page[Any]) -> list[str]:
    return [r.name for r in rows.items]


def test_a_visitor_sees_active_hospitals_and_departments_the_admin_every_one(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    """Story sans jeton: an inactive record is absent; spec §15.4: the admin manages all."""
    port, scene = directory

    seen = port.organizations(OrganizationFilter(), VISITOR)
    managed = port.organizations(OrganizationFilter(), admin(scene))

    assert names(seen) == ["Cardiologie", "Hôpital Nord", "Hôpital Sud"]
    assert seen.total == 3
    assert "Hôpital Fermé" in names(managed)


def test_a_department_is_part_of_its_hospital_and_only_hospitals_have_a_city(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, scene = directory

    (department,) = port.organizations(
        OrganizationFilter(kind=OrganizationKind.DEPARTMENT, part_of=scene.lille.id), VISITOR
    ).items
    (hospital,) = port.organizations(OrganizationFilter(city="lil"), VISITOR).items

    assert isinstance(department, DepartmentRow)
    assert department.hospital_id == scene.lille.id
    assert isinstance(hospital, HospitalRow)
    assert hospital.id == scene.lille.id


def test_near_finds_the_active_sites_within_the_distance(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    """Spec §15.5: `near` on Location; the closed site nearby stays hidden from a visitor."""
    port, scene = directory
    near = LocationFilter(near=Near(50.63, 3.06, 10))

    assert names(port.locations(near, VISITOR)) == ["Hôpital Nord"]
    assert names(port.locations(near, admin(scene))) == ["Hôpital Fermé", "Hôpital Nord"]


def test_a_room_is_part_of_its_site_and_managed_by_its_department(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, scene = directory

    (room,) = port.locations(LocationFilter(part_of=scene.lille.id), VISITOR).items
    by_department = port.locations(LocationFilter(organization=scene.cardiology.id), VISITOR)
    sites = port.locations(LocationFilter(kind=LocationKind.SITE), VISITOR)

    assert isinstance(room, RoomRow)
    assert (room.hospital_id, room.department_id) == (scene.lille.id, scene.cardiology.id)
    assert room.equipment == ("ECG", "Tensiomètre")
    assert [r.id for r in by_department.items] == [scene.room.id]
    assert names(sites) == ["Hôpital Nord", "Hôpital Sud"]


def test_a_page_counts_every_match_and_can_be_read_in_reverse(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, _ = directory

    page = port.organizations(OrganizationFilter(), VISITOR, Paging(count=2, descending=True))

    assert names(page) == ["Hôpital Sud", "Hôpital Nord"]
    assert page.total == 3


def test_a_visitor_sees_types_booked_online_and_staff_also_the_others(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, scene = directory
    by_specialty = ServiceFilter(specialty=scene.specialty.id)

    assert names(port.services(by_specialty, VISITOR)) == ["Consultation"]
    assert names(port.services(by_specialty, clinician(scene))) == ["Consultation", "Échographie"]
    assert port.services(ServiceFilter(specialty=scene.retired.id), VISITOR).items == ()


def test_a_retired_specialty_is_seen_by_the_admin_only(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, scene = directory

    assert names(port.specialties(SpecialtyFilter(), VISITOR)) == ["Cardiologie"]
    assert names(port.specialties(SpecialtyFilter(active=False), admin(scene))) == ["Ancienne"]


def test_a_visitor_sees_active_clinicians_without_their_email_or_phone(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    """Story sans jeton: a clinician's email and phone are not returned."""
    port, scene = directory

    (row,) = port.practitioners(PractitionerFilter(), VISITOR).items

    assert (row.id, row.full_name, row.title) == (scene.clinician.id, "Alice Martin", "Dr")
    assert (row.email, row.phone) == (None, None)


def test_staff_see_every_clinician_with_email_and_phone_and_the_admin_also_admins(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    """Story jeton: staff get every field; only the admin sees admin Practitioners."""
    port, scene = directory

    staff = port.practitioners(PractitionerFilter(), clinician(scene)).items
    everyone = port.practitioners(PractitionerFilter(), admin(scene)).items

    assert [p.full_name for p in staff] == ["Alice Martin", "Bruno Petit"]
    assert staff[0].email == scene.clinician.email.value
    assert staff[0].phone == scene.clinician.phone
    assert (everyone[0].full_name, everyone[0].is_admin) == ("Admin Central", True)


def test_a_visitor_reads_a_role_without_its_weight_reasons_or_offline_types(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, scene = directory

    (public,) = port.roles(RoleFilter(practitioner=scene.clinician.id), VISITOR).items
    (staff,) = port.roles(RoleFilter(practitioner=scene.clinician.id), clinician(scene)).items

    assert public.id == scene.profile.id
    assert (public.weight, public.time_offs[0].reason) == (None, None)
    assert public.service_ids == (scene.online.id,)
    assert [a.id for a in public.availability] == [scene.rule.id]
    assert (staff.weight, staff.time_offs[0].reason) == (3, "Congés")
    assert set(staff.service_ids) == {scene.online.id, scene.offline.id}


def test_roles_match_by_department_hospital_site_room_specialty_and_type(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, scene = directory

    for criteria in (
        RoleFilter(organization=scene.cardiology.id),
        RoleFilter(organization=scene.lille.id),
        RoleFilter(location=scene.room.id),
        RoleFilter(specialty=scene.specialty.id),
        RoleFilter(service=scene.online.id),
    ):
        assert [r.id for r in port.roles(criteria, VISITOR).items] == [scene.profile.id]
    assert port.roles(RoleFilter(organization=scene.paris.id), VISITOR).items == ()


def test_only_the_admin_reads_an_admin_role(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, scene = directory
    mine = RoleFilter(ids=(scene.admin.id,))

    (role,) = port.roles(mine, admin(scene)).items

    assert port.roles(mine, clinician(scene)).items == ()
    assert (role.is_admin, role.practitioner_id) == (True, scene.admin.id)


def test_schedules_match_their_clinician_or_room_and_horizon(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, scene = directory
    on = date(2026, 6, 1)

    (rule,) = port.schedules(
        ScheduleFilter(actor=scene.clinician.id, starts_by=on, ends_from=on), VISITOR
    ).items
    by_room = port.schedules(ScheduleFilter(actor=scene.room.id), VISITOR)
    past = port.schedules(
        ScheduleFilter(actor=scene.clinician.id, ends_from=date(2027, 1, 1)), VISITOR
    )

    assert (rule.id, rule.role_id, rule.room_id) == (scene.rule.id, scene.profile.id, scene.room.id)
    assert [r.id for r in by_room.items] == [scene.rule.id]
    assert past.items == ()


def test_a_former_clinicians_schedule_is_seen_by_staff_only(
    directory: tuple[DirectoryQueries, Directory],
) -> None:
    port, scene = directory
    theirs = ScheduleFilter(actor=scene.former.id)

    assert port.schedules(theirs, VISITOR).items == ()
    assert len(port.schedules(theirs, clinician(scene)).items) == 1
