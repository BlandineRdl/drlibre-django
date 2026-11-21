from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.inbound import (
    MAX_CLINICAL_NOTES,
    AppointmentFile,
    ClinicianAction,
    ClinicianDayView,
    ClinicianEntry,
    ClinicianPatient,
    ClinicianWeekView,
    HistoryActor,
    RoomsDayView,
)
from drlibre.interfaces.web.presenters.availability import (
    GRID_ROWS,
    GRID_START,
    GRID_STEP,
    WEEK_MARGIN,
    GridAppointment,
    WeekView,
    week_view,
)
from drlibre.interfaces.web.presenters.console import NavLink
from drlibre.interfaces.web.presenters.forms import FieldSpec, FormView, build_form
from drlibre.interfaces.web.presenters.portal import (
    REASON_FIELD,
    STATUS_LABELS,
    WeekStripView,
    refusal_text,
    rule_reasons,
    week_strip,
)
from drlibre.interfaces.web.presenters.slots import day_label, local
from drlibre.scheduling.application.ports.inbound import (
    WEEKDAYS,
    AvailabilityRule,
    FreeWeek,
    TimeOff,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page

TODAY_URL = "/workspace/"
CALENDAR_URL = "/workspace/calendar"
PATIENTS_URL = "/workspace/patients"
ROOMS_URL = "/workspace/rooms"
APPOINTMENTS_URL = "/workspace/appointments"
NOT_YOURS = "Not your appointment"
NO_PROFILE = "Votre profil praticien n'est pas encore rattaché ; l'administration s'en charge."
OCCUPIED = "Occupied"
NONE = "—"
_SECTIONS = (
    (TODAY_URL, "Aujourd'hui"),
    (CALENDAR_URL, "Calendrier"),
    (PATIENTS_URL, "Patients"),
    (ROOMS_URL, "Salles"),
    ("/workspace/availability/", "Mes plages"),
    ("/workspace/time-off/", "Mes absences"),
)
# Status actions posted from a button, by the URL segment their endpoint answers.
STATUS_ACTIONS = {
    ClinicianAction.CHECK_IN: ("check-in", "Arrivé"),
    ClinicianAction.COMPLETE: ("complete", "Terminé"),
    ClinicianAction.NO_SHOW: ("no-show", "Absent"),
}
NOTICES = {
    "checked_in": "Le patient est noté arrivé.",
    "completed": "Le rendez-vous est terminé.",
    "no_show": "Le patient est noté absent.",
    "cancelled": "Le rendez-vous est annulé.",
    "moved": "Le rendez-vous est déplacé.",
    "notes": "Les notes cliniques sont enregistrées.",
}
ACTION_LABELS = {
    "booking.appointment_booked": "RDV réservé",
    "booking.appointment_cancelled": "RDV annulé",
    "booking.appointment_rescheduled": "RDV déplacé",
    "booking.appointment_status_changed": "Statut modifié",
    "booking.appointment_notes_written": "Notes cliniques enregistrées",
}
ACTOR_LABELS = {
    HistoryActor.PATIENT: "Patient",
    HistoryActor.CLINICIAN: "Praticien",
    HistoryActor.STAFF: "Personnel",
}
NOTES_FIELD = (
    FieldSpec(
        "clinical_notes",
        "Notes cliniques",
        kind="textarea",
        required=False,
        help=f"{MAX_CLINICAL_NOTES} caractères au plus ; visibles par vous seul.",
    ),
)


def workspace_nav(path: str) -> tuple[NavLink, ...]:
    """The section whose prefix is longest marks the current page."""
    current = max((url for url, _ in _SECTIONS if path.startswith(url)), key=len, default="")
    return tuple(NavLink(url, label, url == current) for url, label in _SECTIONS)


def day_param(raw: str | None) -> date | None:
    """The ?day= or ?week= date, None when missing or unusable, so the use case takes today."""
    try:
        day = date.fromisoformat(raw or "")
    except ValueError:
        return None
    return day if date.min + WEEK_MARGIN <= day <= date.max - WEEK_MARGIN else None


def appointment_url(appointment_id: Id, action: str = "") -> str:
    return f"{APPOINTMENTS_URL}/{appointment_id}" + (f"/{action}" if action else "")


def long_day(day: date) -> str:
    return f"{WEEKDAYS[day.isoweekday() % 7]} {day:%d/%m/%Y}"


@dataclass(frozen=True, slots=True)
class DayNavView:
    previous_url: str
    today_url: str
    next_url: str


def _day_nav(base: str, day: date) -> DayNavView:
    one = timedelta(days=1)
    return DayNavView(f"{base}?day={day - one}", base, f"{base}?day={day + one}")


@dataclass(frozen=True, slots=True)
class ButtonView:
    label: str
    aria_label: str
    url: str


@dataclass(frozen=True, slots=True)
class TileView:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class AgendaRowView:
    time: str
    patient: str
    appointment_type: str
    room: str
    status: str
    buttons: tuple[ButtonView, ...]
    cancel_url: str
    page_url: str
    label: str


@dataclass(frozen=True, slots=True)
class HourGroupView:
    heading: str
    rows: tuple[AgendaRowView, ...]


@dataclass(frozen=True, slots=True)
class TodayPage:
    heading: str
    time_zone: str
    notice: str
    nav: DayNavView
    tiles: tuple[TileView, ...]
    hours: tuple[HourGroupView, ...]
    empty_text: str


def _hours(entry: ClinicianEntry, zone: str) -> str:
    a = entry.appointment
    return f"{local(a.start, zone):%H:%M}-{local(a.end, zone):%H:%M}"


def _buttons(entry: ClinicianEntry, label: str) -> tuple[ButtonView, ...]:
    return tuple(
        ButtonView(text, f"{text} : {label}", appointment_url(entry.appointment.id, segment))
        for action, (segment, text) in STATUS_ACTIONS.items()
        if action in entry.actions
    )


def _cancel_url(entry: ClinicianEntry) -> str:
    allowed = ClinicianAction.CANCEL in entry.actions
    return appointment_url(entry.appointment.id, "cancel") if allowed else ""


def _row(entry: ClinicianEntry, zone: str) -> AgendaRowView:
    time = _hours(entry, zone)
    label = f"{time} {entry.patient_name}"
    return AgendaRowView(
        time=time,
        patient=entry.patient_name,
        appointment_type=entry.appointment_type,
        room=entry.room or NONE,
        status=STATUS_LABELS[entry.appointment.status],
        buttons=_buttons(entry, label),
        cancel_url=_cancel_url(entry),
        page_url=appointment_url(entry.appointment.id),
        label=label,
    )


def _free_slot(instant: datetime | None, zone: str) -> str:
    if instant is None:
        return NONE
    at = local(instant, zone)
    return f"{day_label(at.date())} {at:%H:%M}"


def today_page(view: ClinicianDayView, notice: str = "") -> TodayPage:
    """The day's appointments by local hour with only the actions their status allows."""
    zone, counts = view.time_zone, view.counts
    return TodayPage(
        heading=f"Agenda du {long_day(view.day)}",
        time_zone=zone,
        notice=NOTICES.get(notice, ""),
        nav=_day_nav(TODAY_URL, view.day),
        tiles=(
            TileView("RDV", str(counts.appointments)),
            TileView("Annulés", str(counts.cancelled)),
            TileView("Terminés", str(counts.completed)),
            TileView("Absents", str(counts.no_show)),
            TileView("Prochain créneau libre", _free_slot(view.next_free_slot, zone)),
        ),
        hours=tuple(
            HourGroupView(f"{h.hour:02d}:00", tuple(_row(e, zone) for e in h.entries))
            for h in view.hours
        ),
        empty_text="" if view.hours else "Aucun rendez-vous ce jour.",
    )


def calendar_page(
    view: ClinicianWeekView,
    *,
    rules: tuple[AvailabilityRule, ...],
    time_offs: tuple[TimeOff, ...],
) -> WeekView:
    """The week grid with active appointments named by type in its colour, and time off."""
    appointments = tuple(
        GridAppointment(
            start=e.appointment.start,
            end=e.appointment.end,
            label=e.appointment_type,
            colour=e.type_colour,
            url=appointment_url(e.appointment.id),
        )
        for e in view.entries
    )
    return week_view(
        clinician="",
        title="Mon calendrier",
        time_zone=view.time_zone,
        monday=view.monday,
        rules=rules,
        time_offs=time_offs,
        base_url=CALENDAR_URL,
        appointments=appointments,
    )


@dataclass(frozen=True, slots=True)
class FactView:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class HistoryRowView:
    at: str
    action: str
    actor: str


@dataclass(frozen=True, slots=True)
class AppointmentPage:
    heading: str
    time_zone: str
    notice: str
    refusal: str
    reasons: tuple[str, ...]
    facts: tuple[FactView, ...]
    buttons: tuple[ButtonView, ...]
    cancel_url: str
    notes: FormView
    strip: WeekStripView | None
    history: tuple[HistoryRowView, ...]
    back_url: str


def _when(entry: ClinicianEntry, zone: str) -> str:
    start = local(entry.appointment.start, zone)
    return f"{long_day(start.date())}, {_hours(entry, zone)}"


def appointment_facts(file: AppointmentFile) -> tuple[FactView, ...]:
    entry, zone = file.entry, file.time_zone
    a = entry.appointment
    age = NONE if file.patient_age is None else f"{file.patient_age} ans"
    facts = [
        FactView("Patient", entry.patient_name),
        FactView("Téléphone", entry.patient_phone or NONE),
        FactView("Âge", age),
        FactView("Horaire", _when(entry, zone)),
        FactView("Type", entry.appointment_type),
        FactView("Salle", entry.room or NONE),
        FactView("Motif", a.reason or NONE),
        FactView("Statut", STATUS_LABELS[a.status]),
    ]
    if a.cancellation_reason:
        facts.append(FactView("Motif de l'annulation", a.cancellation_reason))
    return tuple(facts)


def notes_values(file: AppointmentFile) -> dict[str, str]:
    return {"clinical_notes": file.entry.appointment.clinical_notes or ""}


def appointment_page(
    file: AppointmentFile,
    *,
    week: FreeWeek | None,
    notice: str = "",
    refusal: DomainError | None = None,
    notes: Mapping[str, str] | None = None,
    notes_error: DomainError | None = None,
) -> AppointmentPage:
    """Facts, allowed actions, own notes form, week strip when movable and audit history."""
    entry, zone = file.entry, file.time_zone
    a = entry.appointment
    label = f"{_hours(entry, zone)} {entry.patient_name}"
    movable = ClinicianAction.RESCHEDULE in entry.actions and week is not None
    return AppointmentPage(
        heading=f"Rendez-vous de {entry.patient_name}",
        time_zone=zone,
        notice=NOTICES.get(notice, ""),
        refusal=refusal_text(refusal) if refusal else "",
        reasons=rule_reasons(refusal),
        facts=appointment_facts(file),
        buttons=_buttons(entry, label),
        cancel_url=_cancel_url(entry),
        notes=build_form(
            title="Notes cliniques",
            action=appointment_url(a.id, "notes"),
            submit_label="Enregistrer les notes",
            specs=NOTES_FIELD,
            values=notes if notes is not None else notes_values(file),
            error=notes_error,
        ),
        strip=week_strip(week, appointment_url(a.id, "reschedule")) if movable and week else None,
        history=tuple(
            HistoryRowView(
                at=f"{local(h.at, zone):%d/%m/%Y %H:%M}",
                action=ACTION_LABELS.get(h.action, h.action),
                actor=ACTOR_LABELS[h.actor],
            )
            for h in file.history
        ),
        back_url=f"{TODAY_URL}?day={local(a.start, zone).date()}",
    )


@dataclass(frozen=True, slots=True)
class CancelPage:
    heading: str
    time_zone: str
    facts: tuple[FactView, ...]
    form: FormView


def cancel_page(
    file: AppointmentFile, values: Mapping[str, str], error: DomainError | None = None
) -> CancelPage:
    """The reason form; a refusal other than a field error is shown above it."""
    a = file.entry.appointment
    form = build_form(
        title="Annuler le rendez-vous",
        action=appointment_url(a.id, "cancel"),
        submit_label="Confirmer l'annulation",
        specs=REASON_FIELD,
        values=values,
        error=error,
        cancel_url=appointment_url(a.id),
        cancel_label="Retour à la fiche",
    )
    if error is not None and error.code is not ErrorCode.INVALID_INPUT:
        form = replace(form, message=refusal_text(error))
    return CancelPage(
        heading=f"Annuler le rendez-vous de {file.entry.patient_name}",
        time_zone=file.time_zone,
        facts=appointment_facts(file),
        form=form,
    )


@dataclass(frozen=True, slots=True)
class PatientRowView:
    name: str
    phone: str
    last_visit: str
    next_visit: str


@dataclass(frozen=True, slots=True)
class PatientsPage:
    time_zone: str
    search: str
    rows: tuple[PatientRowView, ...]
    empty_text: str
    reset_url: str
    summary: str
    previous_url: str
    next_url: str


def _visit(instant: datetime | None, zone: str) -> str:
    return NONE if instant is None else f"{local(instant, zone):%d/%m/%Y %H:%M}"


def _patients_url(search: str, number: int) -> str:
    query = {"q": search, "page": number} if search else {"page": number}
    return f"{PATIENTS_URL}?{urlencode(query)}"


def patients_page(page: Page[ClinicianPatient], *, search: str, time_zone: str) -> PatientsPage:
    """The clinician's patients with phone and visits in the hospital zone, 20 per page."""
    if page.items:
        empty = ""
    elif search:
        empty = f"Aucun patient ne correspond à « {search} »."
    else:
        empty = "Aucun patient pour l'instant."
    return PatientsPage(
        time_zone=time_zone,
        search=search,
        rows=tuple(
            PatientRowView(
                name=p.full_name,
                phone=p.phone or NONE,
                last_visit=_visit(p.last_visit, time_zone),
                next_visit=_visit(p.next_visit, time_zone),
            )
            for p in page.items
        ),
        empty_text=empty,
        reset_url=PATIENTS_URL if search and not page.items else "",
        summary=f"Page {page.number} sur {page.pages}",
        previous_url=_patients_url(search, page.number - 1) if page.has_previous else "",
        next_url=_patients_url(search, page.number + 1) if page.has_next else "",
    )


@dataclass(frozen=True, slots=True)
class RoomCellView:
    text: str
    english: bool


@dataclass(frozen=True, slots=True)
class RoomRowView:
    name: str
    cells: tuple[RoomCellView, ...]


@dataclass(frozen=True, slots=True)
class RoomsPage:
    heading: str
    time_zone: str
    nav: DayNavView
    times: tuple[str, ...]
    rows: tuple[RoomRowView, ...]
    empty_text: str


def rooms_page(view: RoomsDayView) -> RoomsPage:
    """Active rooms by half hour from 07:00 to 19:00; others' patients never named."""
    zone = view.time_zone
    first = datetime.combine(view.day, GRID_START, ZoneInfo(zone))
    starts = tuple(first + n * GRID_STEP for n in range(GRID_ROWS))
    rows = []
    for room in view.rooms:
        bookings = tuple(b for b in view.bookings if b.room_id == room.id)
        cells = []
        for start in starts:
            booked = next(
                (b for b in bookings if b.start < start + GRID_STEP and start < b.end),
                None,
            )
            if booked is None:
                cells.append(RoomCellView("", english=False))
            elif booked.patient_name is None:
                cells.append(RoomCellView(OCCUPIED, english=True))
            else:
                cells.append(RoomCellView(booked.patient_name, english=False))
        rows.append(RoomRowView(room.name, tuple(cells)))
    return RoomsPage(
        heading=f"Salles du {long_day(view.day)}",
        time_zone=zone,
        nav=_day_nav(ROOMS_URL, view.day),
        times=tuple(f"{s:%H:%M}" for s in starts),
        rows=tuple(rows),
        empty_text="" if view.rooms else "Aucune salle active dans votre département.",
    )
