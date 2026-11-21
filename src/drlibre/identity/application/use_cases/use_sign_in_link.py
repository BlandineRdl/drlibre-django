from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.identity.application.ports.inbound import SignedIn, UseSignInLink
from drlibre.identity.application.ports.outbound import (
    Sessions,
    SignInLinks,
    TokenGenerator,
    Users,
)
from drlibre.identity.domain.session import Session, hash_token
from drlibre.identity.domain.user import Role
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork

UNUSABLE = "Ce lien n'est plus valable. Demandez-en un nouveau."


class UseSignInLinkUseCase(UseSignInLink):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        users: Users,
        sessions: Sessions,
        links: SignInLinks,
        tokens: TokenGenerator,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._users = users
        self._sessions = sessions
        self._links = links
        self._tokens = tokens

    def execute(self, *, token: str, user_agent: str) -> SignedIn:
        at = self._clock.now()
        with self._uow:
            link = self._links.by_token_hash(hash_token(token))
            patient = self._users.get(link.patient_id) if link else None
            domain = patient.email.domain if patient else None
            if (
                link
                and patient
                and link.usable(at)
                and patient.active
                and patient.role is Role.PATIENT
            ):
                session_token = self._tokens.new_token()
                session = Session.after_email_proof(
                    token=session_token, user_id=patient.id, user_agent=user_agent, at=at
                )
                self._links.save(link.used(at))
                self._sessions.add(session)
                self._users.save(patient.signed_in(at=at))
                self._record("identity.link_used", patient.id, domain)
                return SignedIn(
                    token=session_token, role=patient.role, expires_at=session.expires_at
                )
            # The refusal commits its own entry, then raises once the unit has closed.
            self._record("identity.link_refused", None, domain)
        raise DomainError(ErrorCode.UNAUTHENTICATED, UNUSABLE)

    def _record(self, action: str, actor: Id | None, domain: str | None) -> None:
        self._audit.record(
            AuditEntry.from_event(
                actor=actor,
                action=action,
                entity_type="user",
                entity_id=actor,
                at=self._clock.now(),
                metadata={"email_domain": domain} if domain else None,
            )
        )
