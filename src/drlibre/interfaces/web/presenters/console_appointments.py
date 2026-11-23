from collections.abc import Iterator, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

from drlibre.booking.application.ports.inbound import (
    AdminAppointmentFilter,
    AdminAppointmentRow,
    AppointmentFile,
    AppointmentStatus,
    BookingOption,
    ClinicianAction,
    ExportRow,
    Source,
)
from drlibre.identity.application.ports.inbound import PatientMatch
from drlibre.interfaces.web.forms.portal import CancelForm
from drlibre.interfaces.web.presenters.audit_labels import action_label
from drlibre.interfaces.web.presenters.form_page import FormPage
from drlibre.interfaces.web.presenters.forms import ChoiceView
from drlibre.interfaces.web.presenters.portal import (
    STATUS_LABELS,
    WeekStripView,
    refusal_text,
    rule_reasons,
    status_key,
    week_strip,
)
from drlibre.interfaces.web.presenters.slots import day_label, local, zone_name
from drlibre.interfaces.web.presenters.workspace import (
    ACTOR_LABELS,
    NONE,
    STATUS_ACTIONS,
    ButtonView,
    FactView,
    HistoryRowView,
    appointment_facts,
)
from drlibre.organisation.application.ports.inbound import Option
from drlibre.scheduling.application.ports.inbound import FreeWeek
from drlibre.shared_kernel.errors import DomainError
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

CONSOLE_APPOINTMENTS_URL = "/console/appointments/"
BOOK_URL = f"{CONSOLE_APPOINTMENTS_URL}book"
EXPORT_URL = f"{CONSOLE_APPOINTMENTS_URL}export.csv"
ZONE_NOTE = "Heures affichées dans le fuseau de l'hôpital de chaque rendez-vous, nommé."
SOURCE_LABELS = {
    Source.ONLINE: "En ligne",
    Source.ROUND_ROBIN: "Premier disponible",
    Source.STAFF: "Personnel",
}
HEADERS = ("Début", "Patient", "Praticien", "Département", "Type", "Statut", "Source", "Salle")
CSV_HEADERS = (
    "appointment_id",
    "start",
    "end",
    "status",
    "source",
    "patient_id",
    "clinician_id",
    "department_id",
    "appointment_type_id",
    "room_id",
)
NOTICES = {
    "checked_in": "Le patient est noté arrivé.",
    "completed": "Le rendez-vous est terminé.",
    "no_show": "Le patient est noté absent.",
    "cancelled": "Le rendez-vous est annulé.",
    "moved": "Le rendez-vous est déplacé.",
    "booked": "Le rendez-vous est réservé pour le patient.",
}
# A spreadsheet runs a cell starting with one of these as a formula.
_FORMULA_STARTS = ("=", "+", "-", "@", "\t", "\r")


def appointment_url(appointment_id: Id, action: str = "") -> str:
    return f"{CONSOLE_APPOINTMENTS_URL}{appointment_id}" + (f"/{action}" if action else "")


def appointment_filter(query: Mapping[str, str]) -> AdminAppointmentFilter:
    """The list and export filters from the query string; unusable values are dropped."""
    return AdminAppointmentFilter.from_query(
        start=query.get("from"),
        end=query.get("to"),
        department=query.get("department"),
        clinician=query.get("clinician"),
        status=query.get("status"),
        source=query.get("source"),
    )


def filter_query(f: AdminAppointmentFilter) -> dict[str, str]:
    """The kept filters as query parameters, so links carry only usable values."""
    pairs = {
        "from": f.start_date.isoformat() if f.start_date else "",
        "to": f.end_date.isoformat() if f.end_date else "",
        "department": str(f.department_id) if f.department_id else "",
        "clinician": str(f.clinician_id) if f.clinician_id else "",
        "status": f.status.value if f.status else "",
        "source": f.source.value if f.source else "",
    }
    return {k: v for k, v in pairs.items() if v}


INVERTED_DATES = "La date « Du » est après la date « Au » : aucun rendez-vous ne peut correspondre."


@dataclass(frozen=True, slots=True)
class FilterView:
    start: str
    end: str
    departments: tuple[ChoiceView, ...]
    clinicians: tuple[ChoiceView, ...]
    statuses: tuple[ChoiceView, ...]
    sources: tuple[ChoiceView, ...]


@dataclass(frozen=True, slots=True)
class AppointmentRowView:
    label: str
    cells: tuple[str, ...]
    open_url: str
    status_key: str = ""


@dataclass(frozen=True, slots=True)
class AppointmentsListView:
    filters: FilterView
    headers: tuple[str, ...]
    rows: tuple[AppointmentRowView, ...]
    summary: str
    previous_url: str
    next_url: str
    export_url: str
    book_url: str
    zone_note: str
    status_column: int = HEADERS.index("Statut")
    date_warning: str = ""


def _choices(
    options: tuple[Option, ...] | tuple[BookingOption, ...], selected: Id | None
) -> tuple[ChoiceView, ...]:
    return tuple(ChoiceView(str(o.id), o.label, o.id == selected) for o in options)


def _start_cell(row: AdminAppointmentRow) -> str:
    return f"{local(row.appointment.start, row.time_zone):%d/%m/%Y %H:%M} ({row.time_zone})"


def _row(row: AdminAppointmentRow) -> AppointmentRowView:
    a = row.appointment
    start = _start_cell(row)
    return AppointmentRowView(
        label=f"{start} {row.patient_name}",
        cells=(
            start,
            row.patient_name,
            row.clinician_name,
            row.department,
            row.appointment_type,
            STATUS_LABELS[a.status],
            SOURCE_LABELS[a.source],
            row.room or NONE,
        ),
        open_url=appointment_url(a.id),
        status_key=status_key(a.status),
    )


def list_page(
    page: Page[AdminAppointmentRow],
    shown: AdminAppointmentFilter,
    *,
    departments: tuple[Option, ...],
    clinicians: tuple[BookingOption, ...],
) -> AppointmentsListView:
    """Rows latest first, start in each hospital's zone; pagination and export keep the filters."""
    kept = filter_query(shown)

    def url(number: int) -> str:
        return f"{CONSOLE_APPOINTMENTS_URL}?{urlencode({**kept, 'page': number})}"

    noun = "résultat" if page.total == 1 else "résultats"
    inverted = bool(shown.start_date and shown.end_date and shown.start_date > shown.end_date)
    return AppointmentsListView(
        date_warning=INVERTED_DATES if inverted else "",
        filters=FilterView(
            start=kept.get("from", ""),
            end=kept.get("to", ""),
            departments=_choices(departments, shown.department_id),
            clinicians=_choices(clinicians, shown.clinician_id),
            statuses=tuple(
                ChoiceView(s.value, STATUS_LABELS[s], s is shown.status) for s in AppointmentStatus
            ),
            sources=tuple(
                ChoiceView(s.value, label, s is shown.source) for s, label in SOURCE_LABELS.items()
            ),
        ),
        headers=HEADERS,
        rows=tuple(_row(r) for r in page.items),
        summary=f"{page.total} {noun} · page {page.number} sur {page.pages}",
        previous_url=url(page.number - 1) if page.has_previous else "",
        next_url=url(page.number + 1) if page.has_next else "",
        export_url=f"{EXPORT_URL}?{urlencode(kept)}" if kept else EXPORT_URL,
        book_url=BOOK_URL,
        zone_note=ZONE_NOTE,
    )


def csv_cell(value: str) -> str:
    """Prefix an apostrophe so a spreadsheet never runs the cell as a formula."""
    return f"'{value}" if value.startswith(_FORMULA_STARTS) else value


def _utc(instant: datetime) -> str:
    return instant.astimezone(UTC).isoformat()


def csv_rows(rows: tuple[ExportRow, ...]) -> Iterator[tuple[str, ...]]:
    """The header then one line per appointment: ids, UTC ISO 8601 instants and codes."""
    yield CSV_HEADERS
    for r in rows:
        values = (
            str(r.id),
            _utc(r.start),
            _utc(r.end),
            r.status.value,
            r.source.value,
            str(r.patient_id),
            str(r.clinician_id),
            str(r.department_id),
            str(r.appointment_type_id),
            str(r.room_id) if r.room_id else "",
        )
        yield tuple(csv_cell(v) for v in values)


@dataclass(frozen=True, slots=True)
class AdminFilePage:
    heading: str
    time_zone: str
    notice: str
    refusal: str
    reasons: tuple[str, ...]
    facts: tuple[FactView, ...]
    buttons: tuple[ButtonView, ...]
    cancel_url: str
    strip: WeekStripView | None
    history: tuple[HistoryRowView, ...]
    back_url: str


def file_page(
    file: AppointmentFile,
    *,
    week: FreeWeek | None,
    notice: str = "",
    refusal: DomainError | None = None,
) -> AdminFilePage:
    """Facts, the allowed actions, the week strip when movable and the history; never notes."""
    entry, zone = file.entry, file.time_zone
    a = entry.appointment
    label = f"{local(a.start, zone):%d/%m/%Y %H:%M} {entry.patient_name}"
    strip = None
    if ClinicianAction.RESCHEDULE in entry.actions and week is not None:
        strip = week_strip(week, appointment_url(a.id, "reschedule"))

        def week_url(monday: object) -> str:
            return f"{appointment_url(a.id)}?week={monday}#reschedule" if monday else ""

        strip = replace(
            strip,
            previous_url=week_url(week.previous_monday),
            next_url=week_url(week.next_monday),
        )
    return AdminFilePage(
        heading=f"Rendez-vous de {entry.patient_name}",
        time_zone=zone,
        notice=NOTICES.get(notice, ""),
        refusal=refusal_text(refusal) if refusal else "",
        reasons=rule_reasons(refusal),
        facts=(
            *appointment_facts(file),
            FactView("Praticien", file.clinician_name),
            FactView("Hôpital", file.hospital_name),
            FactView("Fuseau", f"{zone_name(zone)} ({zone})"),
            FactView("Source", SOURCE_LABELS[a.source]),
        ),
        buttons=tuple(
            ButtonView(text, f"{text} : {label}", appointment_url(a.id, segment))
            for action, (segment, text) in STATUS_ACTIONS.items()
            if action in entry.actions
        ),
        cancel_url=appointment_url(a.id, "cancel")
        if ClinicianAction.CANCEL in entry.actions
        else "",
        strip=strip,
        history=tuple(
            HistoryRowView(
                at=f"{local(h.at, zone):%d/%m/%Y %H:%M}",
                action=action_label(h.action),
                actor=ACTOR_LABELS[h.actor],
            )
            for h in file.history
        ),
        back_url=CONSOLE_APPOINTMENTS_URL,
    )


@dataclass(frozen=True, slots=True)
class AdminCancelPage:
    heading: str
    time_zone: str
    facts: tuple[FactView, ...]
    form: FormPage


def cancel_page(
    file: AppointmentFile, form: CancelForm, error: DomainError | None = None
) -> AdminCancelPage:
    """The reason form; a refusal other than a field error is shown above it."""
    a = file.entry.appointment
    if error is not None:
        form.refuse(error, refusal_text(error))
    return AdminCancelPage(
        heading=f"Annuler le rendez-vous de {file.entry.patient_name}",
        time_zone=file.time_zone,
        facts=appointment_facts(file),
        form=FormPage(
            "Annuler le rendez-vous",
            appointment_url(a.id, "cancel"),
            "Confirmer l'annulation",
            form,
            cancel_url=appointment_url(a.id),
            cancel_label="Retour à la fiche",
            submit_class="danger",
        ),
    )


@dataclass(frozen=True, slots=True)
class BookChoice:
    """The wizard's choices so far, as raw query values."""

    search: str = ""
    patient: str = ""
    appointment_type: str = ""
    clinician: str = ""
    room: str = ""

    def query(self, **more: str) -> str:
        pairs = {
            "q": self.search,
            "patient": self.patient,
            "type": self.appointment_type,
            "clinician": self.clinician,
            **more,
        }
        return urlencode({k: v for k, v in pairs.items() if v})


@dataclass(frozen=True, slots=True)
class BookPage:
    refusal: str
    reasons: tuple[str, ...]
    choice: BookChoice
    searched: bool
    patients: tuple[ChoiceView, ...]
    types: tuple[ChoiceView, ...]
    clinicians: tuple[ChoiceView, ...]
    rooms: tuple[ChoiceView, ...]
    strip: WeekStripView | None
    time_zone: str
    action: str
    cancel_url: str
    next_slot_text: str = ""
    next_slot_url: str = ""


def _picked(options: tuple[ChoiceView, ...], raw: str) -> tuple[ChoiceView, ...]:
    return tuple(replace(o, selected=o.value == raw) for o in options)


def book_page(
    choice: BookChoice,
    *,
    patients: tuple[PatientMatch, ...],
    types: tuple[BookingOption, ...],
    clinicians: tuple[BookingOption, ...],
    rooms: tuple[BookingOption, ...],
    week: FreeWeek | None,
    error: DomainError | None = None,
    upcoming: tuple[datetime, ...] = (),
) -> BookPage:
    """Patient, type, clinician, then the week's free slots with an optional room."""
    strip = None
    following = None
    if week is not None:
        strip = week_strip(week, BOOK_URL)

        def week_url(monday: object) -> str:
            return f"{BOOK_URL}?{choice.query(week=str(monday))}" if monday else ""

        strip = replace(
            strip,
            previous_url=week_url(week.previous_monday),
            next_url=week_url(week.next_monday),
        )
        sunday = week.monday + timedelta(days=6)
        later = (local(s, week.time_zone) for s in upcoming)
        following = None if week.slots else next((s for s in later if s.date() > sunday), None)
    return BookPage(
        refusal=refusal_text(error) if error else "",
        reasons=rule_reasons(error),
        choice=choice,
        searched=bool(choice.search),
        patients=_picked(
            tuple(
                ChoiceView(str(p.user_id), f"{p.full_name} · {p.email}", False) for p in patients
            ),
            # A single match is the patient searched for, so it is ticked already.
            choice.patient or (str(patients[0].user_id) if len(patients) == 1 else ""),
        ),
        types=_picked(_choices(types, None), choice.appointment_type),
        clinicians=_picked(_choices(clinicians, None), choice.clinician),
        rooms=_picked(_choices(rooms, None), choice.room),
        strip=strip,
        time_zone=week.time_zone if week else "",
        action=BOOK_URL,
        cancel_url=CONSOLE_APPOINTMENTS_URL,
        next_slot_text=(
            f"Prochain créneau libre : {day_label(following.date())} à {following:%H:%M}"
            if following
            else ""
        ),
        next_slot_url=(
            f"{BOOK_URL}?{choice.query(week=following.date().isoformat())}" if following else ""
        ),
    )
