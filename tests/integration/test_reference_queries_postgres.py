import pytest

from drlibre.organisation.infrastructure.django.models import HospitalRecord
from drlibre.organisation.infrastructure.queries import DjangoReferenceQueries
from drlibre.organisation.infrastructure.repositories import DjangoDepartments, DjangoHospitals
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.pagination import PageRequest
from tests import builders_organisation as build

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def hospitals() -> None:
    HospitalRecord.objects.all().delete()
    repository = DjangoHospitals()
    for number in range(22):
        repository.save(build.hospital(name=f"Hôpital Sud {number:02}"))
    for number in range(3):
        repository.save(build.hospital(name=f"Hôpital Nord {number}"))


@pytest.mark.usefixtures("hospitals")
def test_pages_hold_20_rows_with_the_total() -> None:
    queries = DjangoReferenceQueries()

    first = queries.hospitals(PageRequest(number=1))
    second = queries.hospitals(PageRequest(number=2))

    assert (len(first.items), first.total, first.pages) == (20, 25, 2)
    assert (len(second.items), second.has_next, second.has_previous) == (5, False, True)


@pytest.mark.usefixtures("hospitals")
def test_search_matches_name_or_code_case_insensitively() -> None:
    queries = DjangoReferenceQueries()
    one = queries.hospitals(PageRequest()).items[0]

    by_name = queries.hospitals(PageRequest(search="nord"))
    by_code = queries.hospitals(PageRequest(search=one.code.lower()))

    assert by_name.total == 3
    assert [h.code for h in by_code.items] == [one.code]


@pytest.mark.usefixtures("hospitals")
@pytest.mark.parametrize(("page", "rows"), [("abc", 20), ("-1", 20), ("999", 0)])
def test_unusable_page_values_fall_back_or_empty(page: str, rows: int) -> None:
    request = PageRequest.from_query(page=page, search=None)

    assert len(DjangoReferenceQueries().hospitals(request).items) == rows


def test_department_options_name_their_hospital() -> None:
    hospital = build.hospital(name="Hôpital Est")
    DjangoHospitals().save(hospital)
    department = build.department(hospital.id, name="Pédiatrie")
    DjangoDepartments().save(department)

    labels = {o.label for o in DjangoReferenceQueries().department_options()}

    assert f"Pédiatrie ({department.code}) · Hôpital Est" in labels


def test_a_child_added_after_the_check_still_refuses_the_delete_with_its_label() -> None:
    """Un hôpital qui a des départements ne peut pas être supprimé, même ajoutés entre-temps."""
    hospital = build.hospital()
    DjangoHospitals().save(hospital)
    department = build.department(hospital.id, name="Urgences")
    DjangoDepartments().save(department)

    with pytest.raises(DomainError) as refused:
        DjangoHospitals().delete(hospital.id)

    assert refused.value.code is ErrorCode.HAS_DEPENDENTS
    assert refused.value.details == {
        "dependents": [
            {
                "kind": "department",
                "id": str(department.id),
                "label": f"Urgences ({department.code})",
            }
        ]
    }
