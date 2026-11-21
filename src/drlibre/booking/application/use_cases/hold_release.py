from datetime import datetime
from enum import StrEnum

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.outbound import Holds, VerificationCodes
from drlibre.booking.domain.hold import BookingHold


class ReleaseReason(StrEnum):
    REPLACED = "replaced"
    REFUSED = "refused"
    BOOKED = "booked"


def release_hold(
    *,
    holds: Holds,
    codes: VerificationCodes,
    audit: AuditLog,
    hold: BookingHold,
    reason: ReleaseReason,
    at: datetime,
) -> None:
    """Delete the hold and its code, auditing why with the email domain only."""
    codes.delete_for_hold(hold.id)
    holds.delete(hold.id)
    audit.record(
        AuditEntry.from_event(
            actor=None,
            action="booking.hold_released",
            entity_type="booking_hold",
            entity_id=hold.id,
            at=at,
            metadata={"email_domain": hold.details.email_domain, "reason": reason},
        )
    )
