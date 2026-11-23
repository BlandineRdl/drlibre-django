from dataclasses import dataclass
from datetime import datetime

from drlibre.booking.application.ports.inbound import Appointment, HoldSummary
from drlibre.interfaces.web.forms.booking import CodeForm, DetailsForm
from drlibre.interfaces.web.presenters.form_page import FormPage
from drlibre.interfaces.web.presenters.search import SlotLinkView
from drlibre.interfaces.web.presenters.slots import (
    clinician_booking_url,
    first_available_url,
    local,
    slot_label,
)
from drlibre.scheduling.application.ports.inbound import Slot
from drlibre.shared_kernel.ids import Id

STEPS = ("Choix", "Informations", "Code", "Confirmation")
REFRESHED_SLOTS = 12
FIRST_AVAILABLE = "Premier praticien disponible"


@dataclass(frozen=True, slots=True)
class SlotContext:
    """Who, where and what a slot is, as organisation and identity name them."""

    provider_name: str
    department_name: str
    hospital_name: str
    address: str
    time_zone: str
    type_name: str
    duration_minutes: int
    department_id: Id


@dataclass(frozen=True, slots=True)
class StepView:
    label: str
    current: bool


@dataclass(frozen=True, slots=True)
class SummaryView:
    provider_line: str
    type_line: str
    when_line: str
    zone_note: str


@dataclass(frozen=True, slots=True)
class SlotRequest:
    """The slot a visitor chose, as the booking link carries it."""

    type_id: Id
    clinician_id: Id | None
    department_id: Id | None
    start: str

    @property
    def hidden_fields(self) -> tuple[tuple[str, str], ...]:
        fields = [("type", str(self.type_id)), ("start", self.start)]
        if self.clinician_id:
            fields.append(("clinician", str(self.clinician_id)))
        if self.department_id:
            fields.append(("department", str(self.department_id)))
        return tuple(fields)


@dataclass(frozen=True, slots=True)
class DetailsPageView:
    title: str
    steps: tuple[StepView, ...]
    summary: SummaryView
    form: FormPage
    hidden_fields: tuple[tuple[str, str], ...]
    time_zone: str


@dataclass(frozen=True, slots=True)
class ConfirmChoicePageView:
    title: str
    steps: tuple[StepView, ...]
    summary: SummaryView
    action: str
    submit_label: str
    hidden_fields: tuple[tuple[str, str], ...]
    time_zone: str


@dataclass(frozen=True, slots=True)
class CodePageView:
    title: str
    steps: tuple[StepView, ...]
    summary: SummaryView
    held_until: str
    notice: str
    form: FormPage
    resend_action: str
    time_zone: str


@dataclass(frozen=True, slots=True)
class RefusedPageView:
    title: str
    steps: tuple[StepView, ...]
    message: str
    slots_heading: str
    slots: tuple[SlotLinkView, ...]
    empty_text: str
    search_url: str
    time_zone: str


@dataclass(frozen=True, slots=True)
class ConfirmationPageView:
    title: str
    steps: tuple[StepView, ...]
    lines: tuple[str, ...]
    calendar_url: str
    calendar_label: str
    portal_url: str
    portal_label: str
    time_zone: str


def steps(current: int) -> tuple[StepView, ...]:
    return tuple(StepView(label, index == current) for index, label in enumerate(STEPS))


def _summary(context: SlotContext, start: datetime) -> SummaryView:
    provider = context.provider_name or f"{FIRST_AVAILABLE} · {context.department_name}"
    return SummaryView(
        provider_line=provider,
        type_line=f"{context.type_name} · {context.duration_minutes} min · {context.hospital_name}",
        when_line=slot_label(start, context.time_zone),
        zone_note=f"Fuseau {context.time_zone}",
    )


def details_page(
    request: SlotRequest,
    context: SlotContext,
    start: datetime,
    form: DetailsForm,
) -> DetailsPageView:
    return DetailsPageView(
        title="Vos informations",
        steps=steps(1),
        summary=_summary(context, start),
        form=FormPage("Vos informations", "/booking/new", "Recevoir un code", form),
        hidden_fields=request.hidden_fields,
        time_zone=context.time_zone,
    )


def confirm_choice_page(
    request: SlotRequest, context: SlotContext, start: datetime
) -> ConfirmChoicePageView:
    return ConfirmChoicePageView(
        title="Confirmer le rendez-vous",
        steps=steps(0),
        summary=_summary(context, start),
        action="/booking/new",
        submit_label="Confirmer le rendez-vous",
        hidden_fields=request.hidden_fields,
        time_zone=context.time_zone,
    )


def code_page(
    hold: HoldSummary,
    context: SlotContext,
    form: CodeForm,
    *,
    notice: str = "",
) -> CodePageView:
    until = local(hold.expires_at, context.time_zone)
    return CodePageView(
        title="Saisissez votre code",
        steps=steps(2),
        summary=_summary(context, hold.start),
        held_until=f"Créneau tenu jusqu'à {until:%H:%M}",
        notice=notice,
        form=FormPage("Code de vérification", f"/booking/holds/{hold.hold_id}", "Réserver", form),
        resend_action=f"/booking/holds/{hold.hold_id}/resend",
        time_zone=context.time_zone,
    )


def refreshed_slots(
    slots: tuple[Slot, ...],
    *,
    type_id: Id,
    clinician_id: Id | None,
    department_id: Id | None,
    time_zone: str,
) -> tuple[SlotLinkView, ...]:
    links = []
    for slot in slots[:REFRESHED_SLOTS]:
        if clinician_id:
            url = clinician_booking_url(type_id, clinician_id, slot.start)
        elif department_id:
            url = first_available_url(type_id, department_id, slot.start)
        else:
            continue
        links.append(SlotLinkView(slot_label(slot.start, time_zone), url))
    return tuple(links)


def refused_page(
    message: str,
    slots: tuple[SlotLinkView, ...],
    *,
    time_zone: str,
    current_step: int,
    title: str = "Réservation impossible",
) -> RefusedPageView:
    return RefusedPageView(
        title=title,
        steps=steps(current_step),
        message=message,
        slots_heading="Créneaux disponibles" if slots else "",
        slots=slots,
        empty_text="" if slots else "Aucun créneau disponible pour le moment.",
        search_url="/",
        time_zone=time_zone,
    )


def confirmation_page(appointment: Appointment, context: SlotContext) -> ConfirmationPageView:
    start = local(appointment.start, context.time_zone)
    return ConfirmationPageView(
        title="Rendez-vous réservé",
        steps=steps(3),
        lines=(
            f"{context.provider_name} · {context.type_name}",
            f"{context.hospital_name}, {context.address}",
            f"{slot_label(appointment.start, context.time_zone)} "
            f"({start:%d/%m/%Y}), fuseau {context.time_zone}",
        ),
        calendar_url=f"/booking/appointments/{appointment.id}.ics",
        calendar_label="Ajouter à mon agenda (.ics)",
        portal_url="/portal/",
        portal_label="Voir mes rendez-vous",
        time_zone=context.time_zone,
    )
