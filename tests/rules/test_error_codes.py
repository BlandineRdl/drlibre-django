import pytest

from drlibre.shared_kernel.errors import ErrorCode


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("invalid_input", 400),
        ("unauthenticated", 401),
        ("forbidden", 403),
        ("not_found", 404),
        ("conflict", 409),
        ("no_room_available", 409),
        ("no_clinician_available", 409),
        ("invalid_transition", 409),
        ("has_dependents", 409),
        ("rule_violation", 422),
    ],
)
def test_each_spec_code_maps_to_its_http_status(code: str, status: int) -> None:
    assert ErrorCode(code).http_status == status


def test_spec_defines_exactly_ten_codes() -> None:
    assert len(ErrorCode) == 10
