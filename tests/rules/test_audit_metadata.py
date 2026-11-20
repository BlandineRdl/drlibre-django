from datetime import UTC, datetime

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


def test_ids_counts_statuses_domains_and_field_names_are_kept() -> None:
    entry = entry_with(
        {
            "room": Id(),
            "count": 3,
            "status": "BOOKED",
            "email_domain": "example.org",
            "changed": ("full_name", "role"),
        }
    )

    assert dict(entry.metadata)["changed"] == ("full_name", "role")
    assert dict(entry.metadata)["email_domain"] == "example.org"


@pytest.mark.parametrize(
    "value",
    ["ana@example.org", "Douleur thoracique depuis hier", ("ok", "ana@example.org"), 1.5, None],
    ids=["email", "free-text", "email-in-names", "float", "none"],
)
def test_personal_or_free_values_are_refused(value: object) -> None:
    with pytest.raises(UnsafeMetadataError):
        entry_with({"value": value})
