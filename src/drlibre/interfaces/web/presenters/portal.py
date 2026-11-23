from dataclasses import dataclass
from datetime import date, timedelta

from drlibre.booking.application.ports.inbound import (
    AgendaEntry,
    AppointmentStatus,
    BookingRule,
    PatientAction,
    PatientAppointments,
)
from drlibre.identity.application.ports.inbound import User
from drlibre.interfaces.web.forms.portal import CancelForm, ProfileForm
from drlibre.interfaces.web.presenters.console import NavLink
from drlibre.interfaces.web.presenters.form_page import FormPage
from drlibre.interfaces.web.presenters.slots import day_label, local, slot_instant
from drlibre.notifications.application.ports.inbound import Notification, NotificationKind
from drlibre.scheduling.application.ports.inbound import FreeWeek
from drlibre.shared_kernel.booking_policy import (
    BOOKING_LEAD_TIME,
    CANCELLATION_WINDOW,
    MAX_OPEN_ONLINE,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.pagination import Page

APPOINTMENTS_URL = "/portal/appointments"
NOTIFICATIONS_URL = "/portal/notifications"
PROFILE_URL = "/portal/profile"
PASSWORD_URL = "/account/password"  # noqa: S105
SEARCH_URL = "/"
RECEIVED_ZONE_NOTE = "Heures de réception dans le fuseau de l'hôpital du rendez-vous, nommé."
EACH_ZONE_NOTE = "Heures affichées dans le fuseau de chaque hôpital, nommé sur chaque rendez-vous."
STATUS_LABELS = {
    AppointmentStatus.BOOKED: "Réservé",
    AppointmentStatus.CHECKED_IN: "Arrivé",
    AppointmentStatus.COMPLETED: "Terminé",
    AppointmentStatus.CANCELLED: "Annulé",
    AppointmentStatus.NO_SHOW: "Absent",
}
_HOURS = int(CANCELLATION_WINDOW.total_seconds() // 3600)
_MINUTES = int(BOOKING_LEAD_TIME.total_seconds() // 60)
RULE_LABELS = {
    BookingRule.CANCELLATION_WINDOW_CLOSED: f"le rendez-vous commence dans moins de {_HOURS} h",
    BookingRule.LEAD_TIME_TOO_SHORT: f"le nouveau créneau commence dans moins de {_MINUTES} min",
    BookingRule.TYPE_NOT_BOOKABLE_ONLINE: "ce type de rendez-vous ne se réserve pas en ligne",
    BookingRule.OUTSIDE_AVAILABILITY: "ce créneau n'est pas libre",
    BookingRule.TOO_MANY_OPEN_BOOKINGS: f"vous avez déjà {MAX_OPEN_ONLINE} réservations en ligne",
}
KIND_LABELS = {
    NotificationKind.SCHEDULE_CHANGED: "Changement de planning",
    NotificationKind.APPOINTMENT_CANCELLED: "Annulation",
    NotificationKind.APPOINTMENT_REMINDER: "Rappel",
    NotificationKind.WAITLIST_OFFERED: "Liste d'attente",
    NotificationKind.WAITLIST_BOOKED: "Liste d'attente",
}
NOTICES = {
    "cancelled": "Le rendez-vous est annulé.",
    "moved": "Le rendez-vous est déplacé.",
    "booked": "Le créneau proposé est réservé.",
    "saved": "Votre profil est enregistré.",
}


@dataclass(frozen=True, slots=True)
class AppointmentCardView:
    when: str
    lines: tuple[str, ...]
    status: str
    move_url: str
    cancel_url: str
    calendar_url: str
    status_key: str = ""


@dataclass(frozen=True, slots=True)
class HomePageView:
    greeting: str
    next_appointment: AppointmentCardView | None
    no_appointment_text: str
    unread_text: str
    notifications_url: str
    appointments_url: str
    book_url: str


@dataclass(frozen=True, slots=True)
class AppointmentsPageView:
    notice: str
    upcoming: tuple[AppointmentCardView, ...]
    past: tuple[AppointmentCardView, ...]
    no_upcoming_text: str
    no_past_text: str
    book_url: str
    zone_note: str


@dataclass(frozen=True, slots=True)
class CancelPageView:
    appointment: AppointmentCardView
    form: FormPage
    time_zone: str


@dataclass(frozen=True, slots=True)
class SlotButtonView:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class DayView:
    label: str
    slots: tuple[SlotButtonView, ...]
    empty_text: str


@dataclass(frozen=True, slots=True)
class WeekStripView:
    action: str
    week_label: str
    week_value: str
    previous_url: str
    next_url: str
    days: tuple[DayView, ...]
    empty_week_text: str


@dataclass(frozen=True, slots=True)
class ReschedulePageView:
    appointment: AppointmentCardView
    refusal: str
    reasons: tuple[str, ...]
    strip: WeekStripView
    back_url: str
    time_zone: str


@dataclass(frozen=True, slots=True)
class NotificationView:
    title: str
    body: str
    kind: str
    received: str
    state: str
    unread: bool
    mark_url: str


@dataclass(frozen=True, slots=True)
class NotificationsPageView:
    items: tuple[NotificationView, ...]
    empty_text: str
    summary: str
    previous_url: str
    next_url: str
    zone_note: str


@dataclass(frozen=True, slots=True)
class ProfilePageView:
    notice: str
    name: str
    email: str
    form: FormPage
    password_url: str


def appointment_url(entry: AgendaEntry, action: str) -> str:
    return f"{APPOINTMENTS_URL}/{entry.appointment.id}/{action}"


def portal_nav(path: str, home_url: str) -> tuple[NavLink, ...]:
    """The patient's sections; the longest matching prefix marks the current page."""
    sections = (
        (home_url, "Mon espace"),
        (APPOINTMENTS_URL, "Mes RDV"),
        ("/portal/waitlist", "Liste d'attente"),
    )
    subpages = (NOTIFICATIONS_URL, PROFILE_URL)
    matches = [url for url, _ in sections if path.startswith(url) and not path.startswith(subpages)]
    current = max(matches, key=len, default="")
    return tuple(NavLink(url, label, url == current) for url, label in sections)


def status_key(status: AppointmentStatus) -> str:
    """The CSS suffix of a status badge, such as `checked-in`."""
    return status.value.lower().replace("_", "-")


def appointment_day(entry: AgendaEntry) -> date:
    """The local day of the appointment, whose week the strip opens on."""
    return local(entry.appointment.start, entry.time_zone).date()


def appointment_card(entry: AgendaEntry) -> AppointmentCardView:
    """Every field the patient's lists show, with only the actions the rules allow now."""
    a, zone = entry.appointment, entry.time_zone
    start, end = local(a.start, zone), local(a.end, zone)
    place = entry.department if entry.room is None else f"{entry.department} · {entry.room}"
    lines = [
        entry.clinician_name,
        f"{entry.clinician_title} · {entry.specialty}",
        f"{entry.hospital_name}, {entry.hospital_address}",
        place,
        entry.appointment_type,
    ]
    if a.reason:
        lines.append(f"Motif : {a.reason}")
    if a.cancellation_reason:
        lines.append(f"Motif de l'annulation : {a.cancellation_reason}")
    allowed = entry.allowed_actions
    return AppointmentCardView(
        when=(
            f"{day_label(start.date())}/{start:%Y} de {start:%H:%M} à {end:%H:%M}, fuseau {zone}"
        ),
        lines=tuple(lines),
        status=f"Statut : {STATUS_LABELS[a.status]}",
        move_url=appointment_url(entry, "reschedule")
        if PatientAction.RESCHEDULE in allowed
        else "",
        cancel_url=appointment_url(entry, "cancel") if PatientAction.CANCEL in allowed else "",
        calendar_url=f"{APPOINTMENTS_URL}/{a.id}.ics",
        status_key=status_key(a.status),
    )


def home_page(full_name: str, agenda: PatientAppointments, unread: int) -> HomePageView:
    upcoming = agenda.upcoming
    return HomePageView(
        greeting=f"Bonjour {full_name}",
        next_appointment=appointment_card(upcoming[0]) if upcoming else None,
        no_appointment_text="Aucun rendez-vous à venir.",
        unread_text=unread_text(unread),
        notifications_url=NOTIFICATIONS_URL,
        appointments_url=APPOINTMENTS_URL,
        book_url=SEARCH_URL,
    )


def unread_text(count: int) -> str:
    if count == 0:
        return "Aucune notification non lue."
    if count == 1:
        return "1 notification non lue."
    return f"{count} notifications non lues."


def notifications_label(count: int) -> str:
    if count == 0:
        return "Notifications"
    return f"Notifications ({count} non lue{'s' if count > 1 else ''})"


def appointments_page(agenda: PatientAppointments, notice: str = "") -> AppointmentsPageView:
    return AppointmentsPageView(
        notice=NOTICES.get(notice, ""),
        upcoming=tuple(appointment_card(e) for e in agenda.upcoming),
        past=tuple(appointment_card(e) for e in agenda.past),
        no_upcoming_text="Aucun rendez-vous à venir.",
        no_past_text="Aucun rendez-vous passé.",
        book_url=SEARCH_URL,
        zone_note=EACH_ZONE_NOTE,
    )


def refusal_text(error: DomainError) -> str:
    if error.code is ErrorCode.INVALID_TRANSITION:
        status = STATUS_LABELS[AppointmentStatus(error.details["status"])]
        return f"{error.message} Statut actuel : {status}."
    return error.message


def rule_reasons(error: DomainError | None) -> tuple[str, ...]:
    if error is None or error.code is not ErrorCode.RULE_VIOLATION:
        return ()
    return tuple(RULE_LABELS[BookingRule(rule)] for rule in error.details.get("rules", []))


def cancel_page(
    entry: AgendaEntry, form: CancelForm, error: DomainError | None = None
) -> CancelPageView:
    """The reason form; a refusal other than a field error is spelled out above it."""
    if error is not None:
        reasons = "".join(f" {r[0].upper()}{r[1:]}." for r in rule_reasons(error))
        form.refuse(error, refusal_text(error) + reasons)
    page = FormPage(
        "Annuler le rendez-vous",
        appointment_url(entry, "cancel"),
        "Confirmer l'annulation",
        form,
        cancel_url=APPOINTMENTS_URL,
        cancel_label="Retour",
        submit_class="danger",
    )
    return CancelPageView(appointment_card(entry), page, entry.time_zone)


def week_strip(week: FreeWeek, action: str) -> WeekStripView:
    """The week's free slots by local day, each posting its start, with week links."""
    zone = week.time_zone
    by_day: dict[date, list[SlotButtonView]] = {
        week.monday + timedelta(days=n): [] for n in range(7)
    }
    for slot in week.slots:
        at = local(slot.start, zone)
        if at.date() in by_day:
            by_day[at.date()].append(SlotButtonView(f"{at:%H:%M}", slot_instant(slot.start)))
    sunday = week.monday + timedelta(days=6)

    def week_url(monday: date | None) -> str:
        return f"{action}?week={monday.isoformat()}" if monday else ""

    return WeekStripView(
        action=action,
        week_label=f"Semaine du {day_label(week.monday)} au {day_label(sunday)}",
        week_value=week.monday.isoformat(),
        previous_url=week_url(week.previous_monday),
        next_url=week_url(week.next_monday),
        days=tuple(
            DayView(day_label(day), tuple(slots), "" if slots else "Aucun créneau")
            for day, slots in by_day.items()
        ),
        empty_week_text="" if week.slots else "Aucun créneau libre cette semaine.",
    )


def reschedule_page(
    entry: AgendaEntry, week: FreeWeek, error: DomainError | None = None
) -> ReschedulePageView:
    """The week strip of the clinician's free slots, each posting its start; refusals inline."""
    return ReschedulePageView(
        appointment=appointment_card(entry),
        refusal=refusal_text(error) if error else "",
        reasons=rule_reasons(error),
        strip=week_strip(week, appointment_url(entry, "reschedule")),
        back_url=APPOINTMENTS_URL,
        time_zone=week.time_zone,
    )


def _notification(item: Notification, fallback_zone: str) -> NotificationView:
    zone = item.time_zone or fallback_zone
    received = local(item.created_at, zone)
    unread = item.read_at is None
    return NotificationView(
        title=item.title,
        body=item.body,
        kind=KIND_LABELS[item.kind],
        received=f"Reçue le {received:%d/%m/%Y à %H:%M} ({zone})",
        state="Non lue" if unread else "Lue",
        unread=unread,
        mark_url=f"{NOTIFICATIONS_URL}/{item.id}/read" if unread else "",
    )


def notifications_page(page: Page[Notification], fallback_zone: str) -> NotificationsPageView:
    """Each notification dated in its appointment's hospital zone, else in the fallback zone."""
    return NotificationsPageView(
        items=tuple(_notification(n, fallback_zone) for n in page.items),
        empty_text="Aucune notification.",
        summary=f"Page {page.number} sur {page.pages}",
        previous_url=f"{NOTIFICATIONS_URL}?page={page.number - 1}" if page.has_previous else "",
        next_url=f"{NOTIFICATIONS_URL}?page={page.number + 1}" if page.has_next else "",
        zone_note=RECEIVED_ZONE_NOTE,
    )


def profile_values(user: User) -> dict[str, object]:
    return {"phone": user.phone or "", "birth_date": user.birth_date}


def profile_page(
    user: User,
    form: ProfileForm,
    *,
    has_password: bool,
    notice: str = "",
) -> ProfilePageView:
    return ProfilePageView(
        notice=NOTICES.get(notice, ""),
        name=user.full_name,
        email=user.email.value,
        form=FormPage("Mes coordonnées", PROFILE_URL, "Enregistrer", form),
        password_url=PASSWORD_URL if has_password else "",
    )
