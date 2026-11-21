from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from drlibre.booking.application.ports.inbound import WaitlistRow
from drlibre.booking.domain.waitlist import WaitlistEntry
from drlibre.booking.infrastructure.repositories import DjangoWaitlist
from drlibre.bootstrap.container import real_adapters, wire
from drlibre.identity.domain.user import Role
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoDepartments,
    DjangoHospitals,
)
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest
from tests import builders_organisation as build
from tests.builders import stored_user

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

scenarios("../features/booking/l_admin_suit_la_liste_d_attente.feature")

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


@dataclass
class Listing:
    waiting: list[Id] = field(default_factory=list)
    expired: Id | None = None
    page: Page[WaitlistRow] | None = None

    def shown(self) -> Page[WaitlistRow]:
        assert self.page is not None
        return self.page


@pytest.fixture
def listing() -> Listing:
    return Listing()


def stored_type(hospital_name: str) -> Id:
    hospital = build.hospital(name=hospital_name)
    DjangoHospitals().save(hospital)
    department = build.department(hospital.id)
    DjangoDepartments().save(department)
    kind = build.appointment_type(department.id)
    DjangoAppointmentTypes().save(kind)
    return kind.id


def waiting(kind: Id, at: datetime) -> WaitlistEntry:
    entry = WaitlistEntry.join(
        patient_id=stored_user(Role.PATIENT).id,
        appointment_type_id=kind,
        clinician_id=None,
        earliest=NOW,
        latest=NOW + timedelta(days=7),
        at=at,
    )
    DjangoWaitlist().add(entry)
    return entry


@given(
    parsers.parse(
        '{count:d} patients waiting in "{first}" and "{second}", one joining every minute'
    )
)
def patients_waiting(listing: Listing, count: int, first: str, second: str) -> None:
    kinds = (stored_type(first), stored_type(second))
    for minute in range(count):
        entry = waiting(kinds[minute % 2], NOW + timedelta(minutes=minute))
        listing.waiting.append(entry.id)


@given("one expired entry joined before them all")
def expired_entry(listing: Listing) -> None:
    entry = waiting(stored_type("Hôpital Est"), NOW - timedelta(days=1))
    DjangoWaitlist().save(entry.expired())
    listing.expired = entry.id


@when(parsers.parse('the admin lists the "{status}" entries, page "{number}"'))
def lists(listing: Listing, status: str, number: str) -> None:
    request = PageRequest.from_query(page=number, search=None)
    listing.page = wire(real_adapters()).waitlist_queries.page(status, request)


def ids(listing: Listing) -> list[Id]:
    return [row.entry.id for row in listing.shown().items]


@then(parsers.parse("the list shows the 20 oldest waiting entries, oldest first, out of {total:d}"))
def oldest_twenty(listing: Listing, total: int) -> None:
    assert ids(listing) == listing.waiting[:20]
    assert listing.shown().total == total


@then(parsers.parse('the list holds entries of "{names}"'))
def of_hospitals(listing: Listing, names: str) -> None:
    shown = {row.hospital_name for row in listing.shown().items}
    assert shown == {name.strip() for name in names.split(",")}


@then(parsers.parse("the list shows the newest waiting entry only, out of {total:d}"))
def newest_only(listing: Listing, total: int) -> None:
    assert ids(listing) == listing.waiting[20:]
    assert listing.shown().total == total


@then(parsers.parse("the list shows the expired entry only, out of {total:d}"))
def expired_only(listing: Listing, total: int) -> None:
    assert ids(listing) == [listing.expired]
    assert listing.shown().total == total


@then(
    parsers.parse(
        "the list starts with the expired entry, then the oldest waiting ones, out of {total:d}"
    )
)
def everything(listing: Listing, total: int) -> None:
    assert ids(listing) == [listing.expired, *listing.waiting[:19]]
    assert (listing.shown().total, listing.shown().number) == (total, 1)
