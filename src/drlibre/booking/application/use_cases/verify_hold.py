from datetime import datetime

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.inbound import VerifiedBooking, VerifyHold
from drlibre.booking.application.ports.outbound import (
    CodeIssuer,
    Holds,
    OpenedSession,
    PatientAccounts,
    PatientSessions,
    RoundRobinLedger,
    VerificationCodes,
)
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.domain.appointment import Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field

WRONG_CODE = "Code incorrect ou expiré."


class VerifyHoldUseCase(VerifyHold):
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
        accounts: PatientAccounts,
        sessions: PatientSessions,
        ledger: RoundRobinLedger,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._placement = placement
        self._holds = holds
        self._codes = codes
        self._issuer = issuer
        self._accounts = accounts
        self._sessions = sessions
        self._ledger = ledger

    def execute(self, *, hold_id: Id, code: str, user_agent: str) -> VerifiedBooking:
        hold = self._open_hold(hold_id)
        self._check_code(hold, code.strip())
        patient_id, session = self._open_account(hold, user_agent)
        try:
            with self._uow:
                appointment = self._placement.place(
                    patient_id=patient_id,
                    clinician_id=hold.clinician_id,
                    appointment_type_id=hold.appointment_type_id,
                    start=hold.start,
                    source=hold.source,
                    ignoring_hold=hold.id,
                    reason=hold.details.reason,
                )
                if hold.source is Source.ROUND_ROBIN:
                    self._ledger.record(hold.clinician_id, self._clock.now())
                self._release(hold.id)
        except DomainError as failure:
            with self._uow:
                self._release(hold.id)
            return VerifiedBooking(session.token, session.expires_at, None, failure)
        return VerifiedBooking(session.token, session.expires_at, appointment, None)

    def _open_hold(self, hold_id: Id) -> BookingHold:
        hold = self._holds.get(hold_id)
        if hold is None or not hold.is_open(self._clock.now()):
            raise DomainError(ErrorCode.NOT_FOUND, "Réservation provisoire introuvable.")
        return hold

    def _check_code(self, hold: BookingHold, typed: str) -> None:
        with self._uow:
            matched = self._attempt(hold, typed)
        if not matched:
            raise invalid_field("code", WRONG_CODE)

    def _attempt(self, hold: BookingHold, typed: str) -> bool:
        at = self._clock.now()
        stored = self._codes.for_hold_locked(hold.id)
        if stored is not None and stored.is_usable(at):
            if self._issuer.matches(typed, stored.code_hash):
                return True
            self._codes.put(stored.failed_once())
        self._record_failure(hold, at)
        return False

    def _record_failure(self, hold: BookingHold, at: datetime) -> None:
        self._audit.record(
            AuditEntry.from_event(
                actor=None,
                action="booking.code_failed",
                entity_type="booking_hold",
                entity_id=hold.id,
                at=at,
                metadata={"email_domain": hold.details.email_domain},
            )
        )

    def _open_account(self, hold: BookingHold, user_agent: str) -> tuple[Id, OpenedSession]:
        details = hold.details
        try:
            with self._uow:
                patient_id = self._accounts.provide(
                    full_name=details.full_name,
                    email=details.email,
                    birth_date=details.birth_date,
                    phone=details.phone,
                )
                return patient_id, self._sessions.open(patient_id=patient_id, user_agent=user_agent)
        except DomainError:
            with self._uow:
                self._release(hold.id)
            raise

    def _release(self, hold_id: Id) -> None:
        self._codes.delete_for_hold(hold_id)
        self._holds.delete(hold_id)
