from datetime import UTC, datetime

from drlibre.booking.application.ports.inbound import Appointment, AppointmentStatus, HoldSummary
from drlibre.booking.domain.appointment import Source
from drlibre.interfaces.web.presenters.booking import (
    SlotContext,
    SlotRequest,
    code_page,
    confirmation_page,
    details_page,
    refreshed_slots,
)
from drlibre.interfaces.web.presenters.calendar_file import calendar_file
from drlibre.scheduling.application.ports.inbound import Slot
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

KIND = Id()
CLINICIAN = Id()
DEPARTMENT = Id()
START = datetime(2026, 11, 23, 8, tzinfo=UTC)
CONTEXT = SlotContext(
    provider_name="Dr Alice Martin",
    department_name="Cardiologie",
    hospital_name="Hôpital Nord",
    address="1 rue de la Paix, 59000 Lille",
    time_zone="Europe/Paris",
    type_name="Consultation",
    duration_minutes=20,
    department_id=DEPARTMENT,
)
REQUEST = SlotRequest(KIND, CLINICIAN, None, "2026-11-23T08:00:00Z")


def appointment() -> Appointment:
    return Appointment(
        id=Id(),
        patient_id=Id(),
        clinician_id=CLINICIAN,
        appointment_type_id=KIND,
        room_id=None,
        start=START,
        end=datetime(2026, 11, 23, 8, 20, tzinfo=UTC),
        status=AppointmentStatus.BOOKED,
        source=Source.ONLINE,
        reason="Douleur à la poitrine",
    )


def test_the_details_page_names_the_provider_the_slot_and_the_hospital_zone() -> None:
    """Story réservation : le récapitulatif donne praticien, créneau et fuseau de l'hôpital."""
    view = details_page(REQUEST, CONTEXT, START, {})

    assert view.summary.provider_line == "Dr Alice Martin"
    assert view.summary.when_line == "lun. 23/11 09:00"
    assert view.summary.zone_note == "Fuseau Europe/Paris"
    assert [s.label for s in view.steps if s.current] == ["Informations"]
    assert ("type", str(KIND)) in view.hidden_fields


def test_the_details_page_ties_each_error_to_its_field_and_focuses_the_first() -> None:
    """Story réservation : erreurs rattachées aux champs, focus sur le premier invalide."""
    error = DomainError(
        ErrorCode.INVALID_INPUT,
        "Corrigez les champs.",
        {
            "fields": [
                {"field": "email", "message": "Saisissez une adresse email valide."},
                {"field": "full_name", "message": "Ce champ est obligatoire."},
            ]
        },
    )

    view = details_page(REQUEST, CONTEXT, START, {"email": "x"}, error)

    focused = [f.name for f in view.form.fields if f.autofocus]
    assert focused == ["full_name"]
    described = {f.name: f.described_by for f in view.form.fields}
    assert described["email"] == "error-email"


def test_a_first_available_booking_shows_the_department_until_a_provider_is_chosen() -> None:
    """Story premier disponible : le praticien n'est nommé qu'une fois la réservation tenue."""
    context = SlotContext(
        provider_name="",
        department_name="Cardiologie",
        hospital_name="Hôpital Nord",
        address="",
        time_zone="Europe/Paris",
        type_name="Consultation",
        duration_minutes=20,
        department_id=DEPARTMENT,
    )

    view = details_page(SlotRequest(KIND, None, DEPARTMENT, "x"), context, START, {})

    assert view.summary.provider_line == "Premier praticien disponible · Cardiologie"
    assert ("department", str(DEPARTMENT)) in view.hidden_fields


def test_the_code_page_gives_the_hold_expiry_in_the_hospital_zone() -> None:
    """Story réservation : « Créneau tenu jusqu'à » en heure de l'hôpital."""
    hold = HoldSummary(
        hold_id=Id(),
        clinician_id=CLINICIAN,
        appointment_type_id=KIND,
        start=START,
        end=START,
        expires_at=datetime(2026, 11, 20, 9, 42, tzinfo=UTC),
        open=True,
        first_available=False,
    )

    view = code_page(hold, CONTEXT)

    assert view.held_until == "Créneau tenu jusqu'à 10:42"
    assert view.form.action == f"/booking/holds/{hold.hold_id}"
    assert view.resend_action.endswith("/resend")


def test_refreshed_slots_link_to_the_same_kind_of_booking_as_the_chosen_one() -> None:
    """Story règle enfreinte : créneau pris, créneaux rafraîchis réservables comme avant."""
    slots = (Slot(START, START),)

    specific = refreshed_slots(
        slots, type_id=KIND, clinician_id=CLINICIAN, department_id=None, time_zone="Europe/Paris"
    )
    first = refreshed_slots(
        slots, type_id=KIND, clinician_id=None, department_id=DEPARTMENT, time_zone="Europe/Paris"
    )

    assert f"clinician={CLINICIAN}" in specific[0].url
    assert f"department={DEPARTMENT}" in first[0].url
    assert first[0].label == "lun. 23/11 09:00"


def test_the_confirmation_links_the_calendar_file_and_the_patient_portal() -> None:
    """Story réservation : page de confirmation avec .ics et lien vers les rendez-vous."""
    booked = appointment()

    view = confirmation_page(booked, CONTEXT)

    assert view.calendar_url == f"/booking/appointments/{booked.id}.ics"
    assert view.portal_url == "/portal/"
    assert "Hôpital Nord, 1 rue de la Paix, 59000 Lille" in view.lines[1]


def test_the_calendar_file_is_rfc_5545_in_utc_without_the_reason() -> None:
    """Story réservation : .ics en UTC (Z), fins de ligne CRLF, sans le motif."""
    booked = appointment()

    text = calendar_file(
        booked,
        summary="Consultation, avec Dr Alice Martin",
        location="Hôpital Nord, 1 rue de la Paix",
        stamped_at=datetime(2026, 11, 20, 10, tzinfo=UTC),
    )

    lines = text.split("\r\n")
    assert lines[0] == "BEGIN:VCALENDAR"
    assert lines[-2:] == ["END:VCALENDAR", ""]
    assert "DTSTART:20261123T080000Z" in lines
    assert "DTEND:20261123T082000Z" in lines
    assert f"UID:{booked.id}@drlibre" in lines
    assert "SUMMARY:Consultation\\, avec Dr Alice Martin" in lines
    assert "\n" not in text.replace("\r\n", "")
    assert "Douleur" not in text


def test_a_long_calendar_line_is_folded_at_75_octets() -> None:
    """Story réservation : .ics, lignes repliées à 75 octets selon la RFC 5545."""
    text = calendar_file(
        appointment(),
        summary="é" * 80,
        location="x",
        stamped_at=datetime(2026, 11, 20, 10, tzinfo=UTC),
    )

    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))
