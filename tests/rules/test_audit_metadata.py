from datetime import UTC, datetime
from enum import StrEnum

import pytest

from drlibre.audit.application.ports.outbound import AuditEntry, UnsafeMetadataError
from drlibre.shared_kernel.ids import Id

AT = datetime(2026, 11, 20, 10, tzinfo=UTC)


def entry_with(metadata: dict[str, object]) -> AuditEntry:
    return AuditEntry.from_event(
        actor=None,
        action="user.created",
        entity_type="user",
        entity_id=Id(),
        at=AT,
        metadata=metadata,
    )


class Status(StrEnum):
    BOOKED = "BOOKED"


def test_ids_counts_statuses_domains_and_field_names_are_kept() -> None:
    """Spec §4: audit metadata holds ids, counts, status values and changed field names."""
    entry = entry_with(
        {
            "room": Id(),
            "count": 3,
            "status": Status.BOOKED,
            "email_domain": "example.org",
            "changed": ("full_name", "role"),
        }
    )

    assert dict(entry.metadata)["changed"] == ("full_name", "role")
    assert dict(entry.metadata)["email_domain"] == "example.org"


@pytest.mark.parametrize(
    "value",
    [
        "ana@example.org",
        "Ana",
        "Douleur thoracique",
        ("ok", "ana@example.org"),
        ("Ana",),
        1.5,
        None,
    ],
    ids=["email", "first-name", "free-text", "email-in-names", "name-in-names", "float", "none"],
)
def test_personal_or_free_values_are_refused(value: object) -> None:
    """Spec §4: metadata never holds names, emails or free text."""
    with pytest.raises(UnsafeMetadataError):
        entry_with({"value": value})
