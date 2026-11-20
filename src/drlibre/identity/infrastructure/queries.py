from django.db.models import Q

from drlibre.identity.application.ports.inbound import (
    Role,
    StaffLookup,
    StaffMember,
    User,
    UserQueries,
)
from drlibre.identity.infrastructure.django.models import UserRecord
from drlibre.identity.infrastructure.repositories import to_user
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import PAGE_SIZE, Page, PageRequest


def _member(record: UserRecord) -> StaffMember:
    return StaffMember(Id(record.id), record.full_name, Role(record.role), record.active)


class DjangoUserQueries(UserQueries, StaffLookup):
    def users(self, request: PageRequest) -> Page[User]:
        rows = UserRecord.objects.order_by("full_name", "email")
        if request.search:
            rows = rows.filter(
                Q(full_name__icontains=request.search) | Q(email__icontains=request.search)
            )
        window = rows[request.offset : request.offset + PAGE_SIZE]
        return Page(tuple(to_user(r) for r in window), rows.count(), request.number)

    def user(self, user_id: Id) -> User | None:
        record = UserRecord.objects.filter(id=user_id.value).first()
        return to_user(record) if record else None

    def staff_member(self, user_id: Id) -> StaffMember | None:
        record = UserRecord.objects.filter(id=user_id.value).first()
        return _member(record) if record else None

    def active_clinicians(self) -> tuple[StaffMember, ...]:
        rows = UserRecord.objects.filter(role=Role.CLINICIAN.value, active=True).order_by(
            "full_name"
        )
        return tuple(_member(r) for r in rows)

    def named_like(self, text: str) -> frozenset[Id]:
        ids = UserRecord.objects.filter(full_name__icontains=text).values_list("id", flat=True)
        return frozenset(Id(pk) for pk in ids)
