import json
from collections.abc import Callable
from datetime import UTC, date, datetime

import pytest
from django.conf import settings
from django.http import QueryDict
from django.test import Client, RequestFactory

from drlibre.identity.domain.user import Role
from drlibre.interfaces.fhir import FhirParser
from drlibre.interfaces.fhir.access import caller
from drlibre.interfaces.fhir.bundle import searchset
from drlibre.interfaces.fhir.diff import changes
from drlibre.interfaces.fhir.outcome import error_outcome
from drlibre.interfaces.fhir.params import DateBound, Prefix, date_bound, search_query
from drlibre.interfaces.fhir.registry import Interaction, ParamType, ResourceRules, SearchParam
from drlibre.interfaces.fhir.version import etag, expected_version, version_id
from drlibre.interop.application.ports.inbound import StaleVersionError
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from tests.builders import stored_session, stored_user
from tests.fhir.conftest import Call

# A resource for the conventions alone, never registered, so nothing serves it.
SAMPLE = ResourceRules(
    type="Sample",
    interactions=(Interaction.SEARCH,),
    search=(SearchParam("name", ParamType.STRING), SearchParam("date", ParamType.DATE)),
    sorts=("name",),
)


def refusal(action: Callable[[], object]) -> DomainError:
    with pytest.raises(DomainError) as raised:
        action()
    return raised.value


@pytest.mark.integration
@pytest.mark.django_db
def test_a_false_bearer_token_is_refused_as_unauthenticated(call: Call) -> None:
    """Story jeton : un jeton invalide renvoie unauthenticated (401)."""
    response = call("GET", "/fhir/metadata", token="faux")

    issue = response.json()["issue"][0]
    assert response.status_code == 401
    assert response["WWW-Authenticate"] == "Bearer"
    assert issue["code"] == "login"
    assert issue["details"]["coding"][0]["code"] == "unauthenticated"


@pytest.mark.integration
def test_a_valid_bearer_token_is_accepted(call: Call, role_token: Callable[..., str]) -> None:
    response = call("GET", "/fhir/metadata", token=role_token(Role.PATIENT))

    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
def test_a_session_cookie_alone_reads_fhir_as_a_visitor(fhir_client: Client) -> None:
    """Plan E8: under /fhir the cookie is ignored; a forced password change would refuse it."""
    user = stored_user(Role.CLINICIAN, must_change=True)
    fhir_client.cookies[settings.SESSION_COOKIE_NAME] = stored_session(user)

    response = fhir_client.get("/fhir/metadata")

    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.django_db
def test_a_cross_origin_fhir_call_is_not_refused_by_the_same_origin_guard(
    fhir_client: Client,
) -> None:
    """Plan E8: FHIR carries no ambient credential, so another origin reaches its handlers."""
    response = fhir_client.post("/fhir/metadata", headers={"Origin": "https://evil.example"})

    assert response.status_code == 405


def test_an_interaction_needing_a_token_refuses_a_visitor() -> None:
    request = RequestFactory().post("/fhir/Sample")

    assert refusal(lambda: caller(request)).code is ErrorCode.UNAUTHENTICATED


@pytest.mark.parametrize("code", list(ErrorCode), ids=[c.value for c in ErrorCode])
def test_every_refusal_becomes_an_operation_outcome_with_its_status(code: ErrorCode) -> None:
    """Spec §15.1: errors are OperationOutcome, statuses from spec §4."""
    details = {"fields": [{"field": "birthDate", "message": "Date invalide."}]}

    response = error_outcome(DomainError(code, "Refusé.", details))

    (issue,) = json.loads(response.content)["issue"]
    assert response.status_code == code.http_status
    assert response["Content-Type"] == "application/fhir+json; charset=utf-8"
    assert issue["details"] == {
        "coding": [{"system": "urn:drlibre:error-code", "code": code.value}],
        "text": "Refusé.",
    }
    assert issue["expression"] == ["birthDate"]
    assert json.loads(issue["diagnostics"]) == details


@pytest.mark.integration
def test_an_undeclared_parameter_is_refused_with_an_operation_outcome(call: Call) -> None:
    response = call("GET", "/fhir/metadata?foo=1")

    issue = response.json()["issue"][0]
    assert response.status_code == 400
    assert issue["code"] == "invalid"
    assert issue["expression"] == ["foo"]


def test_an_undeclared_search_parameter_or_sort_is_refused() -> None:
    for raw in ("colour=red", "_sort=date", "_include=Sample:x"):
        found = refusal(lambda raw=raw: search_query(QueryDict(raw), SAMPLE))
        assert found.code is ErrorCode.INVALID_INPUT, raw


@pytest.mark.parametrize(
    ("raw", "count"), [("", 20), ("_count=5", 5), ("_count=500", 100)], ids=["default", "5", "500"]
)
def test_a_page_holds_twenty_results_by_default_and_never_more_than_a_hundred(
    raw: str, count: int
) -> None:
    assert search_query(QueryDict(raw), SAMPLE).count == count


@pytest.mark.parametrize("raw", ["_count=0", "_count=-1", "_count=abc", "_page=0"])
def test_a_count_or_page_below_one_or_not_a_number_is_refused(raw: str) -> None:
    assert refusal(lambda: search_query(QueryDict(raw), SAMPLE)).code is ErrorCode.INVALID_INPUT


def test_a_declared_search_keeps_its_parameters_and_descending_sort() -> None:
    query = search_query(QueryDict("name=Mar&_sort=-name&_page=2"), SAMPLE)

    assert query.params == (("name", "Mar"),)
    assert query.sort == ("-name",)
    assert query.page == 2


def test_a_searchset_links_its_pages_from_the_public_base_url() -> None:
    query = search_query(QueryDict("name=Mar&_count=10&_page=2"), SAMPLE)

    bundle = searchset(resource_type="Sample", query=query, total=25, entries=())

    links = {link.relation: link.url for link in bundle.link}
    base = f"{settings.PUBLIC_BASE_URL}/fhir/Sample?name=Mar&_count=10&_page="
    assert bundle.total == 25
    assert links == {"self": f"{base}2", "next": f"{base}3", "previous": f"{base}1"}


def test_the_last_page_has_no_next_link() -> None:
    query = search_query(QueryDict("_page=3&_count=10"), SAMPLE)

    bundle = searchset(resource_type="Sample", query=query, total=25, entries=())

    assert {link.relation for link in bundle.link} == {"self", "previous"}


def test_a_search_without_result_answers_a_bundle_without_entry() -> None:
    """Spec §15.1 : un Bundle FHIR R4 n'a jamais de tableau vide."""
    query = search_query(QueryDict(""), SAMPLE)

    bundle = searchset(resource_type="Sample", query=query, total=0, entries=())

    assert "entry" not in bundle.model_dump(by_alias=True, exclude_none=True)


def test_a_date_parameter_takes_its_prefix_and_a_day_or_an_aware_instant() -> None:
    assert date_bound("date", "ge2026-11-23") == DateBound(Prefix.GE, date(2026, 11, 23))
    assert date_bound("date", "2026-11-23T09:00:00+00:00") == DateBound(
        Prefix.EQ, datetime(2026, 11, 23, 9, tzinfo=UTC)
    )
    for raw in ("ne2026-11-23", "2026-11-23T09:00:00", "demain"):
        assert refusal(lambda raw=raw: date_bound("date", raw)).code is ErrorCode.INVALID_INPUT


def test_a_version_changes_with_its_state_and_reads_back_from_if_match() -> None:
    version = version_id("a", 1)

    assert version == version_id("a", 1)
    assert version != version_id("a", 2)
    assert len(version) == 12
    assert expected_version(etag(version)) == version
    assert expected_version(f'"{version}"') == version
    assert expected_version(None) is None


@pytest.mark.parametrize("content_type", ["application/fhir+json", "application/json"])
def test_a_body_is_read_as_fhir_json_or_json(content_type: str) -> None:
    request = RequestFactory().post("/fhir/Sample", data="{}", content_type=content_type)

    assert FhirParser().parse_body(request) == {}


def test_a_body_in_another_format_is_refused() -> None:
    request = RequestFactory().post("/fhir/Sample", data="a=1", content_type="text/plain")

    assert refusal(lambda: FhirParser().parse_body(request)).code is ErrorCode.INVALID_INPUT


def test_an_update_keeps_its_writable_changes_and_refuses_the_others() -> None:
    """Plan E8: a field of another role is forbidden, a fixed one invalid_input on its path."""
    current = {"A.mine": 1, "A.theirs": 1, "A.fixed": 1}

    def change(**fields: int) -> object:
        return changes(
            current,
            current | {f"A.{k}": v for k, v in fields.items()},
            writable=frozenset({"A.mine"}),
            reserved=frozenset({"A.theirs"}),
        )

    assert change(mine=2) == frozenset({"A.mine"})
    assert refusal(lambda: change(theirs=2)).code is ErrorCode.FORBIDDEN
    fixed = refusal(lambda: change(fixed=2))
    assert fixed.code is ErrorCode.INVALID_INPUT
    assert fixed.details["fields"][0]["field"] == "A.fixed"


def test_a_stale_version_is_a_conflict_answered_412() -> None:
    """Spec §15.1: an If-Match naming an older version fails with 412."""
    response = error_outcome(StaleVersionError())

    (issue,) = json.loads(response.content)["issue"]
    assert response.status_code == 412
    assert (issue["code"], issue["details"]["coding"][0]["code"]) == ("conflict", "conflict")
