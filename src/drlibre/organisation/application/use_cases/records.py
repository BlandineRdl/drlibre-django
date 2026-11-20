from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Protocol

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.organisation.application.ports.outbound import Records
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.dependents import Dependents
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import changed_fields, invalid_field


class Coded(Protocol):
    @property
    def id(self) -> Id: ...

    @property
    def code(self) -> str: ...

    @property
    def created_at(self) -> datetime: ...


type Build[T] = Callable[..., T]


class RecordWrites:
    """The save and delete steps every referential record shares: one unit, one audit entry."""

    def __init__(self, *, clock: Clock, uow: UnitOfWork, audit: AuditLog, entity_type: str) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._entity_type = entity_type

    def existing[T: Coded](self, records: Records[T], record_id: Id) -> T:
        record = records.get(record_id)
        if record is None:
            raise DomainError(ErrorCode.NOT_FOUND, "Élément introuvable.", {"id": str(record_id)})
        return record

    def save[T: Coded](
        self,
        *,
        records: Records[T],
        build: Build[T],
        actor: Id | None,
        record_id: Id | None,
        fields: Mapping[str, str],
        check: Callable[[T | None, T], None] = lambda before, after: None,
        written: Callable[[T | None, T], None] = lambda before, after: None,
    ) -> Id:
        at = self._clock.now()
        before = self.existing(records, record_id) if record_id else None
        after = build(
            fields,
            id=before.id if before else Id(),
            created_at=before.created_at if before else at,
            at=at,
        )
        if records.code_taken(after.code, except_id=after.id):
            raise invalid_field("code", "Ce code est déjà utilisé.")
        check(before, after)
        with self._uow:
            records.save(after)
            written(before, after)
            action = "updated" if before else "created"
            changed = changed_fields(before, after, ignore=("updated_at",)) if before else ()
            self._record(actor, action, after.id, {"changed": changed} if before else {}, at)
        return after.id

    def delete[T: Coded](
        self,
        *,
        records: Records[T],
        actor: Id | None,
        record_id: Id,
        dependents: Callable[[T], Dependents],
        message: str,
    ) -> None:
        record = self.existing(records, record_id)
        with self._uow:
            # Checked in the delete's transaction; the repository refuses rows added meanwhile.
            dependents(record).refuse_if_any(message)
            records.delete(record.id)
            self._record(actor, "deleted", record.id, {}, self._clock.now())

    def _record(
        self,
        actor: Id | None,
        action: str,
        entity_id: Id,
        metadata: dict[str, object],
        at: datetime,
    ) -> None:
        self._audit.record(
            AuditEntry.from_event(
                actor=actor,
                action=f"{self._entity_type}.{action}",
                entity_type=self._entity_type,
                entity_id=entity_id,
                at=at,
                metadata=metadata,
            )
        )
