from dataclasses import dataclass
from datetime import datetime, timedelta
from urllib.parse import urlencode

from drlibre.booking.application.ports.inbound import (
    WaitlistRow,
    WaitlistStatus,
)
from drlibre.interfaces.web.forms.portal import WaitlistJoinForm
from drlibre.interfaces.web.presenters.form_page import FormPage
from drlibre.interfaces.web.presenters.forms import (
    Choice,
    ChoiceView,
)
from drlibre.interfaces.web.presenters.portal import rule_reasons
from drlibre.interfaces.web.presenters.slots import day_label, local
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.pagination import Page

WAITLIST_URL = "/portal/waitlist"
CONSOLE_WAITLIST_URL = "/console/waitlist/"
WAITLIST_STATUS_LABELS = {
    WaitlistStatus.WAITING: "En attente",
    WaitlistStatus.OFFERED: "Créneau proposé",
    WaitlistStatus.BOOKED: "RDV obtenu",
    WaitlistStatus.EXPIRED: "Expirée",
}
STATUS_CHOICES = tuple(Choice(s.value, label) for s, label in WAITLIST_STATUS_LABELS.items())
ZONE_NOTE = "Heures affichées dans le fuseau de l'hôpital de chaque entrée, nommé."
NOTICES = {
    "joined": "Inscription enregistrée.",
    "added": "Le patient est inscrit sur la liste d'attente.",
    "offered": "Un créneau est proposé au patient.",
    "booked": "Le rendez-vous est réservé pour le patient.",
}
HEADERS = (
    "Inscrite le",
    "Patient",
    "Type",
    "Praticien",
    "Fenêtre",
    "Statut",
    "Proposé",
)


@dataclass(frozen=True, slots=True)
class EntryCardView:
    title: str
    lines: tuple[str, ...]
    status: str
    offered: str
    accept_url: str


@dataclass(frozen=True, slots=True)
class WaitlistPageView:
    notice: str
    refusal: str
    entries: tuple[EntryCardView, ...]
    empty_text: str
    form: FormPage
    zone_note: str


@dataclass(frozen=True, slots=True)
class WaitlistRowView:
    label: str
    cells: tuple[str, ...]
    offer_url: str
    accept_url: str


@dataclass(frozen=True, slots=True)
class WaitlistListView:
    notice: str
    refusal: str
    status: str
    status_choices: tuple[ChoiceView, ...]
    headers: tuple[str, ...]
    rows: tuple[WaitlistRowView, ...]
    summary: str
    previous_url: str
    next_url: str
    add_url: str
    zone_note: str


def window_text(row: WaitlistRow) -> str:
    """The window as the dates the patient chose, its last day included."""
    first = local(row.entry.earliest, row.time_zone)
    last = local(row.entry.latest, row.time_zone) - timedelta(days=1)
    return f"du {first:%d/%m/%Y} au {last:%d/%m/%Y}"


def offered_text(row: WaitlistRow) -> str:
    if row.offered_start is None or row.entry.status is not WaitlistStatus.OFFERED:
        return ""
    at = local(row.offered_start, row.time_zone)
    return f"{day_label(at.date())}/{at:%Y} {at:%H:%M}, fuseau {row.time_zone}"


def refusal_text(error: DomainError | None) -> str:
    """The refusal with the entry's status or the broken rules spelled out."""
    if error is None:
        return ""
    text = error.message
    if error.code is ErrorCode.INVALID_TRANSITION and "status" in error.details:
        text += (
            f" Statut actuel : {WAITLIST_STATUS_LABELS[WaitlistStatus(error.details['status'])]}."
        )
    return text + "".join(f" {r[0].upper()}{r[1:]}." for r in rule_reasons(error))


def status_filter(raw: str) -> str:
    """A known status, else empty for every status."""
    return raw if raw in set(WaitlistStatus) else ""


def entry_card(row: WaitlistRow, now: datetime) -> EntryCardView:
    entry = row.entry
    accept = row.offered_start is not None and entry.acceptable_by_patient(row.offered_start, now)
    lines = [row.hospital_name, window_text(row).capitalize()]
    if row.clinician_name:
        lines.insert(0, f"Praticien préféré : {row.clinician_name}")
    offered = offered_text(row)
    return EntryCardView(
        title=row.appointment_type,
        lines=tuple(lines),
        status=f"Statut : {WAITLIST_STATUS_LABELS[entry.status]}",
        offered=f"Proposé : {offered}" if offered else "",
        accept_url=f"{WAITLIST_URL}/{entry.id}/accept" if accept else "",
    )


def waitlist_page(
    rows: tuple[WaitlistRow, ...],
    form: WaitlistJoinForm,
    now: datetime,
    *,
    notice: str = "",
    error: DomainError | None = None,
) -> WaitlistPageView:
    return WaitlistPageView(
        notice=NOTICES.get(notice, ""),
        refusal=refusal_text(error),
        entries=tuple(entry_card(r, now) for r in rows),
        empty_text="Aucune inscription pour l'instant.",
        form=FormPage("S'inscrire", WAITLIST_URL, "S'inscrire", form),
        zone_note=ZONE_NOTE,
    )


def _row(row: WaitlistRow, now: datetime) -> WaitlistRowView:
    entry = row.entry
    created = local(entry.created_at, row.time_zone)
    accept = row.offered_start is not None and entry.acceptable_by_staff(row.offered_start, now)
    base = f"{CONSOLE_WAITLIST_URL}{entry.id}"
    return WaitlistRowView(
        label=f"{row.patient_name}, {row.appointment_type}",
        cells=(
            f"{created:%d/%m/%Y %H:%M}, fuseau {row.time_zone}",
            row.patient_name,
            f"{row.appointment_type} · {row.hospital_name}",
            row.clinician_name or "Indifférent",
            window_text(row),
            WAITLIST_STATUS_LABELS[entry.status],
            offered_text(row) or "—",
        ),
        offer_url=f"{base}/offer" if entry.offerable else "",
        accept_url=f"{base}/accept" if accept else "",
    )


def console_list(
    page: Page[WaitlistRow],
    status: str,
    now: datetime,
    *,
    notice: str = "",
    error: DomainError | None = None,
) -> WaitlistListView:
    """Rows oldest first; pagination keeps the status filter."""
    shown = status_filter(status)

    def url(number: int) -> str:
        query = {"page": number, **({"status": shown} if shown else {})}
        return f"{CONSOLE_WAITLIST_URL}?{urlencode(query)}"

    noun = "résultat" if page.total == 1 else "résultats"
    return WaitlistListView(
        notice=NOTICES.get(notice, ""),
        refusal=refusal_text(error),
        status=shown,
        status_choices=tuple(
            ChoiceView(c.value, c.label, c.value == shown) for c in STATUS_CHOICES
        ),
        headers=HEADERS,
        rows=tuple(_row(r, now) for r in page.items),
        summary=f"{page.total} {noun} · page {page.number} sur {page.pages}",
        previous_url=url(page.number - 1) if page.has_previous else "",
        next_url=url(page.number + 1) if page.has_next else "",
        add_url=f"{CONSOLE_WAITLIST_URL}new",
        zone_note=ZONE_NOTE,
    )
