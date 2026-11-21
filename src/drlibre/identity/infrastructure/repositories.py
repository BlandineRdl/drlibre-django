from datetime import datetime

from drlibre.identity.application.ports.outbound import Sessions, SignInLinks, Users
from drlibre.identity.domain.session import Session
from drlibre.identity.domain.sign_in_link import SignInLink
from drlibre.identity.domain.user import Email, Role, User
from drlibre.identity.infrastructure.django.models import (
    SessionRecord,
    SignInLinkRecord,
    UserRecord,
)
from drlibre.shared_kernel.ids import Id


def to_user(record: UserRecord) -> User:
    return User(
        id=Id(record.id),
        email=Email(record.email),
        full_name=record.full_name,
        role=Role(record.role),
        active=record.active,
        password_hash=record.password_hash,
        must_change_password=record.must_change_password,
        last_login_at=record.last_login_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        phone=record.phone,
        birth_date=record.birth_date,
        email_verified_at=record.email_verified_at,
    )


class DjangoUsers(Users):
    def get(self, user_id: Id) -> User | None:
        record = UserRecord.objects.filter(id=user_id.value).first()
        return to_user(record) if record else None

    def by_email(self, email: Email) -> User | None:
        record = UserRecord.objects.filter(email=email.value).first()
        return to_user(record) if record else None

    def save(self, user: User) -> None:
        UserRecord.objects.update_or_create(
            id=user.id.value,
            defaults={
                "email": user.email.value,
                "full_name": user.full_name,
                "role": user.role.value,
                "active": user.active,
                "password_hash": user.password_hash,
                "must_change_password": user.must_change_password,
                "last_login_at": user.last_login_at,
                "phone": user.phone,
                "birth_date": user.birth_date,
                "email_verified_at": user.email_verified_at,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
            },
        )

    def delete(self, user_id: Id) -> None:
        UserRecord.objects.filter(id=user_id.value).delete()


def _to_session(record: SessionRecord) -> Session:
    return Session(
        id=Id(record.id),
        token_hash=record.token_hash,
        user_id=Id(record.user_id),
        expires_at=record.expires_at,
        lifetime=record.lifetime,
        extendable=record.extendable,
        user_agent=record.user_agent,
    )


class DjangoSessions(Sessions):
    def add(self, session: Session) -> None:
        SessionRecord.objects.create(
            id=session.id.value,
            token_hash=session.token_hash,
            user_id=session.user_id.value,
            expires_at=session.expires_at,
            lifetime=session.lifetime,
            extendable=session.extendable,
            user_agent=session.user_agent,
        )

    def by_token_hash(self, token_hash: str) -> Session | None:
        record = SessionRecord.objects.filter(token_hash=token_hash).first()
        return _to_session(record) if record else None

    def save(self, session: Session) -> None:
        SessionRecord.objects.filter(id=session.id.value).update(expires_at=session.expires_at)

    def delete(self, session_id: Id) -> None:
        SessionRecord.objects.filter(id=session_id.value).delete()

    def delete_for_user(self, user_id: Id) -> int:
        deleted, _ = SessionRecord.objects.filter(user_id=user_id.value).delete()
        return deleted


def _to_link(record: SignInLinkRecord) -> SignInLink:
    return SignInLink(
        id=Id(record.id),
        token_hash=record.token_hash,
        patient_id=Id(record.patient_id),
        expires_at=record.expires_at,
        used_at=record.used_at,
        cancelled_at=record.cancelled_at,
    )


class DjangoSignInLinks(SignInLinks):
    def add(self, link: SignInLink) -> None:
        SignInLinkRecord.objects.create(
            id=link.id.value,
            token_hash=link.token_hash,
            patient_id=link.patient_id.value,
            expires_at=link.expires_at,
            used_at=link.used_at,
            cancelled_at=link.cancelled_at,
        )

    def by_token_hash(self, token_hash: str) -> SignInLink | None:
        # The row lock makes a link single-use when two requests race to consume it.
        record = SignInLinkRecord.objects.select_for_update().filter(token_hash=token_hash).first()
        return _to_link(record) if record else None

    def cancel_open_for(self, patient_id: Id, *, at: datetime) -> None:
        SignInLinkRecord.objects.filter(
            patient_id=patient_id.value, used_at__isnull=True, cancelled_at__isnull=True
        ).update(cancelled_at=at)

    def save(self, link: SignInLink) -> None:
        SignInLinkRecord.objects.filter(id=link.id.value).update(
            used_at=link.used_at, cancelled_at=link.cancelled_at
        )
