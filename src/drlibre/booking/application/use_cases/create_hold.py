from datetime import datetime, timedelta

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import CreateHold, HoldCreated
from drlibre.booking.application.ports.outbound import (
    BookableType,
    BookingNotices,
    CodeIssuer,
    Holds,
    ScheduleLocks,
    VerificationCodes,
)
from drlibre.booking.application.use_cases.hold_release import ReleaseReason, release_hold
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.domain.appointment import Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.verification_code import VerificationCode
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.rate_limit import RateLimiter, within_hourly_limits
from drlibre.shared_kernel.unit_of_work import UnitOfWork

HOLDS_PER_EMAIL = 3
TOO_MANY = "Trop de demandes, réessayez plus tard."


def refuse_over_limit(
    limiter: RateLimiter, *, kind: str, email: str, network: str, per_email: int, per_network: int
) -> None:
    """Count one request for the email and the network; too_many_requests past either limit."""
    if not within_hourly_limits(
        limiter,
        kind=kind,
        email=email,
        network=network,
        per_email=per_email,
        per_network=per_network,
    ):
        raise DomainError(ErrorCode.RULE_VIOLATION, TOO_MANY, {"rules": ["too_many_requests"]})


class CreateHoldUseCase(CreateHold):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        placement: Placement,
        holds: Holds,
        codes: VerificationCodes,
        issuer: CodeIssuer,
        locks: ScheduleLocks,
        limiter: RateLimiter,
        notices: BookingNotices,
        network_hourly_limit: int,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._placement = placement
        self._holds = holds
        self._codes = codes
        self._issuer = issuer
        self._locks = locks
        self._limiter = limiter
        self._notices = notices
        self._network_limit = network_hourly_limit

    def execute(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id | None,
        start: datetime,
        full_name: str,
        birth_date: str,
        email: str,
        phone: str,
        reason: str,
        accepted_terms: bool,
        network: str,
    ) -> HoldCreated:
        at = self._clock.now()
        details = VisitorDetails.parse(
            full_name=full_name,
            birth_date=birth_date,
            email=email,
            phone=phone,
            reason=reason,
            accepted_terms=accepted_terms,
            today=at.date(),
        )
        refuse_over_limit(
            self._limiter,
            kind="hold",
            email=details.email,
            network=network,
            per_email=HOLDS_PER_EMAIL,
            per_network=self._network_limit,
        )
        with self._uow:
            self._locks.lock_email(details.email)
            previous = self._holds.open_for_email(details.email, at)
            if previous is not None:
                self._release(previous, at)
            kind = self._placement.bookable_type(appointment_type_id)

            def open_hold(chosen: Id) -> BookingHold:
                return self._open_hold(kind, chosen, start, details, at, clinician_id is None)

            if clinician_id is not None:
                hold = open_hold(clinician_id)
            else:
                ranked = self._placement.ranked_candidates(kind, start)
                hold = self._placement.first_free(ranked, open_hold)
            issued = self._issuer.issue()
            self._codes.put(
                VerificationCode.issue(
                    hold_id=hold.id, email=details.email, code_hash=issued.code_hash, at=at
                )
            )
            self._notices.code_sent(email=details.email, code=issued.code)
            self._audit.record(self._created_entry(hold, at))
        return HoldCreated(hold.id, hold.clinician_id, hold.expires_at)

    def _open_hold(
        self,
        kind: BookableType,
        chosen: Id,
        start: datetime,
        details: VisitorDetails,
        at: datetime,
        first_available: bool,
    ) -> BookingHold:
        self._placement.clinician_of(kind, chosen)
        self._locks.lock_clinician(chosen)
        end = start + timedelta(minutes=kind.duration_minutes)
        self._placement.refuse_conflicts(None, chosen, start, end, ignoring_hold=None)
        self._placement.refuse_rule_violations(None, chosen, kind, start, ignoring_hold=None)
        hold = BookingHold.open(
            clinician_id=chosen,
            appointment_type_id=kind.id,
            start=start,
            duration=end - start,
            source=Source.ROUND_ROBIN if first_available else Source.ONLINE,
            details=details,
            at=at,
        )
        self._holds.add(hold)
        return hold

    def _release(self, hold: BookingHold, at: datetime) -> None:
        release_hold(
            holds=self._holds,
            codes=self._codes,
            audit=self._audit,
            hold=hold,
            reason=ReleaseReason.REPLACED,
            at=at,
        )

    def _created_entry(self, hold: BookingHold, at: datetime) -> AuditEntry:
        return AuditEntry.from_event(
            actor=None,
            action="booking.hold_created",
            entity_type="booking_hold",
            entity_id=hold.id,
            at=at,
            metadata={
                "email_domain": hold.details.email_domain,
                "clinician_id": hold.clinician_id,
                "appointment_type_id": hold.appointment_type_id,
                "source": hold.source,
            },
        )
