from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import RequestSignInLink
from drlibre.identity.application.ports.outbound import (
    LinkNotices,
    SignInLinks,
    TokenGenerator,
    Users,
)
from drlibre.identity.domain.sign_in_link import LINKS_PER_EMAIL_PER_HOUR, SignInLink
from drlibre.identity.domain.user import Email, Role
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.rate_limit import RateLimiter, within_hourly_limits
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class RequestSignInLinkUseCase(RequestSignInLink):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        users: Users,
        links: SignInLinks,
        tokens: TokenGenerator,
        notices: LinkNotices,
        limiter: RateLimiter,
        network_hourly_limit: int,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._links = links
        self._tokens = tokens
        self._notices = notices
        self._limiter = limiter
        self._network_limit = network_hourly_limit

    def execute(self, *, email: str, network: str) -> None:
        address = Email.parse(email)
        # Both counters move on every request, known address or not, so the limit reveals nothing.
        if not within_hourly_limits(
            self._limiter,
            kind="link",
            email=address.value,
            network=network,
            per_email=LINKS_PER_EMAIL_PER_HOUR,
            per_network=self._network_limit,
        ):
            return
        patient = self._users.by_email(address)
        if patient is None or not patient.active or patient.role is not Role.PATIENT:
            return
        at = self._clock.now()
        token = self._tokens.new_token()
        with self._uow:
            self._links.cancel_open_for(patient.id, at=at)
            self._links.add(SignInLink.issue(token=token, patient_id=patient.id, at=at))
            self._notices.link_sent(email=patient.email.value, token=token)
            self._audit.record(
                AuditEntry.from_event(
                    actor=patient.id,
                    action="identity.link_requested",
                    entity_type="user",
                    entity_id=patient.id,
                    at=at,
                    metadata={"email_domain": address.domain},
                )
            )
