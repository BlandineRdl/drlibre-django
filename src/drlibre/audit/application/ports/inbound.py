from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest


@dataclass(frozen=True, slots=True)
class AuditRecordView:
    """Who did what and when to one entity; metadata stays in the audit context."""

    actor_id: Id | None
    action: str
    at: datetime


@dataclass(frozen=True, slots=True)
class AuditFilter:
    """Optional narrowing of the journal; `start` included, `end` excluded."""

    actor_id: Id | None = None
    entity_type: str | None = None
    start: datetime | None = None
    end: datetime | None = None

    @classmethod
    def from_query(
        cls,
        *,
        actor_id: Id | None,
        entity_type: str | None,
        start: str | None,
        end: str | None,
        time_zone: str,
        entity_types: tuple[str, ...],
    ) -> "AuditFilter":
        """Local days of the zone, both included; an unknown type or a bad date means none."""
        zone = ZoneInfo(time_zone)
        first, last = _date_or_none(start), _date_or_none(end)
        return cls(
            actor_id=actor_id,
            entity_type=entity_type if entity_type in entity_types else None,
            start=datetime.combine(first, time(), zone) if first else None,
            end=datetime.combine(last + timedelta(days=1), time(), zone) if last else None,
        )


def _date_or_none(raw: str | None) -> date | None:
    try:
        return date.fromisoformat(raw) if raw else None
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class AuditRow:
    """One journal line; the actor is empty before a user is known."""

    at: datetime
    actor_id: Id | None
    action: str
    entity_type: str
    entity_id: Id | None
    correlation_id: str


class AuditQueries(Protocol):
    def has_acted(self, actor: Id) -> bool:
        """True when the user is the actor of at least one audit entry."""
        ...

    def entries_for(self, entity_type: str, entity_id: Id) -> tuple[AuditRecordView, ...]:
        """The entity's audit entries, oldest first; empty when there is none."""
        ...

    def page(self, audit_filter: AuditFilter, request: PageRequest) -> Page[AuditRow]:
        """Matching entries, newest first then id, 20 a page, with the total."""
        ...

    def entity_types(self) -> tuple[str, ...]:
        """Every entity type the journal holds, sorted."""
        ...


@dataclass(frozen=True, slots=True)
class JournalQuery:
    """The journal's raw filters; an unusable value means no filter."""

    email: str | None
    entity_type: str | None
    start: str | None
    end: str | None
    request: PageRequest


@dataclass(frozen=True, slots=True)
class AuditJournal:
    page: Page[AuditRow]
    audit_filter: AuditFilter
    entity_types: tuple[str, ...]
    # Email of each actor of the page.
    emails: Mapping[Id, str]
    # Zone the filter dates are read in and the times shown in.
    time_zone: str


class ViewAuditJournal(Protocol):
    def execute(self, *, actor_id: Id, query: JournalQuery) -> AuditJournal:
        """One journal page with its actors' emails; an unknown email matches no entry."""
        ...
