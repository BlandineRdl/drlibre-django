from drlibre.booking.application.emails import code_email
from drlibre.booking.application.ports.inbound import ResendCode
from drlibre.booking.application.ports.outbound import CodeIssuer, Holds, VerificationCodes
from drlibre.booking.application.use_cases.create_hold import refuse_over_limit
from drlibre.booking.domain.verification_code import VerificationCode
from drlibre.notifications.application.ports.outbound import EmailOutbox
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.rate_limit import RateLimiter
from drlibre.shared_kernel.unit_of_work import UnitOfWork

RESENDS_PER_EMAIL = 3


class ResendCodeUseCase(ResendCode):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        holds: Holds,
        codes: VerificationCodes,
        issuer: CodeIssuer,
        limiter: RateLimiter,
        outbox: EmailOutbox,
        network_hourly_limit: int,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._holds = holds
        self._codes = codes
        self._issuer = issuer
        self._limiter = limiter
        self._outbox = outbox
        self._network_limit = network_hourly_limit

    def execute(self, *, hold_id: Id, network: str) -> None:
        at = self._clock.now()
        hold = self._holds.get(hold_id)
        if hold is None or not hold.is_open(at):
            raise DomainError(ErrorCode.NOT_FOUND, "Réservation provisoire introuvable.")
        refuse_over_limit(
            self._limiter,
            kind="code",
            email=hold.email,
            network=network,
            per_email=RESENDS_PER_EMAIL,
            per_network=self._network_limit,
        )
        issued = self._issuer.issue()
        with self._uow:
            self._codes.put(
                VerificationCode.issue(
                    hold_id=hold.id, email=hold.email, code_hash=issued.code_hash, at=at
                )
            )
            self._outbox.queue(code_email(to=hold.email, code=issued.code))
