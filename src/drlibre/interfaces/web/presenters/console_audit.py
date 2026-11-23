import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlencode

from drlibre.audit.application.ports.inbound import AuditFilter, AuditRow
from drlibre.interfaces.web.presenters.audit_labels import action_label, entity_label
from drlibre.interfaces.web.presenters.choices import ChoiceView
from drlibre.interfaces.web.presenters.slots import local
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

AUDIT_URL = "/console/audit/"
HEADERS = ("Heure", "Acteur", "Action", "Entité", "Identifiant de corrélation")
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


@dataclass(frozen=True, slots=True)
class AuditPageView:
    actor: str
    entity_type: str
    start: str
    end: str
    entity_choices: tuple[ChoiceView, ...]
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    summary: str
    previous_url: str
    next_url: str
    zone_note: str


def actor_email(raw: str | None) -> str:
    """The trimmed, lower-cased email; a malformed one means no actor filter."""
    value = (raw or "").strip().lower()
    return value if len(value) <= 254 and _EMAIL.fullmatch(value) else ""


def _row(row: AuditRow, emails: Mapping[Id, str], time_zone: str) -> tuple[str, ...]:
    kind = entity_label(row.entity_type)
    entity = f"{kind} {row.entity_id}" if row.entity_id else kind
    actor = emails.get(row.actor_id, "") if row.actor_id else ""
    return (
        f"{local(row.at, time_zone):%d/%m/%Y %H:%M:%S}",
        actor,
        action_label(row.action),
        entity,
        row.correlation_id,
    )


def audit_page(
    page: Page[AuditRow],
    audit_filter: AuditFilter,
    *,
    email: str,
    entity_types: tuple[str, ...],
    emails: Mapping[Id, str],
    time_zone: str,
) -> AuditPageView:
    """Newest first; the usable filters are shown again and kept by the pagination."""
    shown_type = audit_filter.entity_type or ""
    start = f"{local(audit_filter.start, time_zone):%Y-%m-%d}" if audit_filter.start else ""
    end = (
        f"{local(audit_filter.end - timedelta(days=1), time_zone):%Y-%m-%d}"
        if audit_filter.end
        else ""
    )
    kept = {"actor": email, "entity_type": shown_type, "from": start, "to": end}

    def url(number: int) -> str:
        query = {"page": number, **{k: v for k, v in kept.items() if v}}
        return f"{AUDIT_URL}?{urlencode(query)}"

    noun = "entrée" if page.total <= 1 else "entrées"
    return AuditPageView(
        actor=email,
        entity_type=shown_type,
        start=start,
        end=end,
        entity_choices=tuple(ChoiceView(t, entity_label(t), t == shown_type) for t in entity_types),
        headers=HEADERS,
        rows=tuple(_row(r, emails, time_zone) for r in page.items),
        summary=f"{page.total} {noun} · page {page.number} sur {page.pages}",
        previous_url=url(page.number - 1) if page.has_previous else "",
        next_url=url(page.number + 1) if page.has_next else "",
        zone_note=f"Heures affichées dans le fuseau {time_zone}.",
    )
