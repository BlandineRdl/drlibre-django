import dataclasses
from datetime import UTC, date, datetime, timedelta
from typing import Any

from drlibre.booking.application.ports.inbound import (
    AgendaEntry,
    AppointmentStatus,
    PatientAction,
    PatientAppointments,
)
from drlibre.interfaces.web.presenters.portal import (
    appointment_card,
    appointments_page,
    cancel_page,
    home_page,
    notifications_label,
    notifications_page,
    profile_page,
    reschedule_page,
)
from drlibre.notifications.application.ports.inbound import AppointmentEvent, Notification
from drlibre.scheduling.application.ports.inbound import FreeWeek, Slot
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page
from tests.builders_booking import existing_appointment, patient_user

START = datetime(2026, 11, 23, 8, tzinfo=UTC)
BOTH = frozenset({PatientAction.CANCEL, PatientAction.RESCHEDULE})


def entry(**changes: Any) -> AgendaEntry:
    appointment = existing_appointment(
        patient_id=Id(),
        clinician_id=Id(),
        start=START,
        end=START + timedelta(minutes=30),
        reason="Douleur au genou",
    )
    made = AgendaEntry(
        appointment=appointment,
        clinician_name="Alice Martin",
        clinician_title="Dr",
        specialty="Cardiologie",
        hospital_name="Hôpital Nord",
        hospital_address="1 rue de la Paix, 59000 Lille",
        time_zone="Europe/Paris",
        department="Rythmologie",
        room="Salle 1",
        appointment_type="Consultation",
        allowed_actions=BOTH,
    )
    return dataclasses.replace(made, **changes)


def test_a_card_shows_every_field_in_the_named_hospital_time_zone() -> None:
    """Story « retrouve ses RDV » : début et fin dans le fuseau de l'hôpital, qui est nommé."""
    card = appointment_card(entry())

    assert card.when == "lun. 23/11/2026 de 09:00 à 09:30, fuseau Europe/Paris"
    assert card.status == "Statut : Réservé"
    assert card.lines == (
        "Alice Martin",
        "Dr · Cardiologie",
        "Hôpital Nord, 1 rue de la Paix, 59000 Lille",
        "Rythmologie · Salle 1",
        "Consultation",
        "Motif : Douleur au genou",
    )
    assert card.calendar_url.endswith(".ics")


def test_a_card_offers_only_the_actions_the_rules_allow() -> None:
    """Stories « annule » et « déplace » : actions proposées seulement quand permises."""
    both = appointment_card(entry())
    cancel_only = appointment_card(entry(allowed_actions=frozenset({PatientAction.CANCEL})))
    none = appointment_card(entry(allowed_actions=frozenset()))

    assert both.move_url.endswith("/reschedule")
    assert both.cancel_url.endswith("/cancel")
    assert (cancel_only.move_url, bool(cancel_only.cancel_url)) == ("", True)
    assert (none.move_url, none.cancel_url) == ("", "")
    assert none.calendar_url


def test_a_cancelled_card_shows_its_status_and_cancellation_reason_without_a_room() -> None:
    cancelled = dataclasses.replace(
        entry().appointment,
        status=AppointmentStatus.CANCELLED,
        cancelled_at=START,
        cancellation_reason="Empêchement",
    )

    card = appointment_card(entry(appointment=cancelled, room=None, allowed_actions=frozenset()))

    assert card.status == "Statut : Annulé"
    assert "Rythmologie" in card.lines
    assert "Motif de l'annulation : Empêchement" in card.lines


def test_the_lists_have_empty_states_and_a_status_message() -> None:
    view = appointments_page(PatientAppointments((), ()), "cancelled")

    assert view.notice == "Le rendez-vous est annulé."
    assert (view.no_upcoming_text, view.no_past_text) == (
        "Aucun rendez-vous à venir.",
        "Aucun rendez-vous passé.",
    )
    assert appointments_page(PatientAppointments((), ()), "unknown").notice == ""


def test_the_home_page_greets_and_counts_unread_notifications() -> None:
    """Story « accueil » : salutation, prochain RDV, nombre de notifications non lues."""
    soonest = entry()
    view = home_page("Léa Martin", PatientAppointments((soonest, entry()), ()), 2)
    empty = home_page("Léa Martin", PatientAppointments((), ()), 0)

    assert view.greeting == "Bonjour Léa Martin"
    assert view.next_appointment == appointment_card(soonest)
    assert view.unread_text == "2 notifications non lues."
    assert view.book_url == "/"
    assert empty.next_appointment is None
    assert empty.unread_text == "Aucune notification non lue."


def test_the_menu_counts_unread_notifications_in_words() -> None:
    assert notifications_label(0) == "Notifications"
    assert notifications_label(1) == "Notifications (1 non lue)"
    assert notifications_label(3) == "Notifications (3 non lues)"


def test_a_refused_cancellation_names_the_broken_rule_in_words() -> None:
    """Story « annule » : moins de 24 h refusé avec cancellation_window_closed."""
    error = DomainError(
        ErrorCode.RULE_VIOLATION,
        "L'annulation enfreint une règle.",
        {"rules": ["cancellation_window_closed"]},
    )

    view = cancel_page(entry(), {"reason": "Empêchement"}, error)

    assert view.form.message == (
        "L'annulation enfreint une règle. Le rendez-vous commence dans moins de 24 h."
    )
    assert view.form.fields[0].value == "Empêchement"
    assert (view.form.submit_label, view.form.cancel_label) == ("Confirmer l'annulation", "Retour")


def test_a_refused_transition_names_the_current_status() -> None:
    error = DomainError(
        ErrorCode.INVALID_TRANSITION,
        "Ce rendez-vous ne permet pas ce changement.",
        {"status": "COMPLETED"},
    )

    view = cancel_page(entry(), {}, error)

    assert view.form.message.endswith("Statut actuel : Terminé.")


def test_the_week_strip_groups_free_slots_by_local_day_and_posts_their_start() -> None:
    """Story « déplace » : bandeau à la semaine des créneaux libres du même praticien."""
    week = FreeWeek(
        monday=date(2026, 11, 23),
        previous_monday=None,
        next_monday=date(2026, 11, 30),
        time_zone="Europe/Paris",
        slots=(Slot(START, START + timedelta(minutes=30)),),
    )
    error = DomainError(
        ErrorCode.RULE_VIOLATION,
        "Le déplacement enfreint une règle.",
        {"rules": ["lead_time_too_short", "outside_availability"]},
    )

    view = reschedule_page(entry(), week, error)

    monday, tuesday = view.days[0], view.days[1]
    assert (monday.label, monday.slots[0].label, monday.slots[0].value) == (
        "lun. 23/11",
        "09:00",
        "2026-11-23T08:00:00Z",
    )
    assert (tuesday.slots, tuesday.empty_text) == ((), "Aucun créneau")
    assert view.week_label == "Semaine du lun. 23/11 au dim. 29/11"
    assert view.previous_url == ""
    assert view.next_url.endswith("/reschedule?week=2026-11-30")
    assert view.reasons == (
        "le nouveau créneau commence dans moins de 120 min",
        "ce créneau n'est pas libre",
    )
    assert view.empty_week_text == ""


def test_unread_notifications_are_marked_by_text_not_colour_alone() -> None:
    """Story « notifications » : non lue signalée par texte ; plus récentes en premier."""
    at = datetime(2026, 11, 20, 9, tzinfo=UTC)
    unread = Notification.for_event(
        event=AppointmentEvent.BOOKED,
        recipient_id=Id(),
        appointment_id=Id(),
        start=START,
        zone_name="Europe/Paris",
        at=at,
    )
    read = dataclasses.replace(unread, id=Id(), read_at=at)

    view = notifications_page(Page((unread, read), total=2, number=1), "Europe/Paris")

    first, second = view.items
    assert (first.state, first.kind, bool(first.mark_url)) == (
        "Non lue",
        "Changement de planning",
        True,
    )
    assert first.received == "Reçue le 20/11/2026 à 10:00 (Europe/Paris)"
    assert (second.state, second.mark_url) == ("Lue", "")
    assert notifications_page(Page((), 0, 1), "Europe/Paris").empty_text == "Aucune notification."


def test_the_profile_shows_the_password_link_only_to_a_password_holder() -> None:
    """Story « profil » : changement de mot de passe pour qui en a un, caché sinon."""
    user = patient_user(Id())

    holder = profile_page(user, {}, has_password=True)
    passwordless = profile_page(user, {}, has_password=False, notice="saved")

    assert holder.password_url == "/account/password"
    assert passwordless.password_url == ""
    assert passwordless.notice == "Votre profil est enregistré."
    assert (holder.name, holder.email) == ("Patient Test", "patient@example.org")
    assert [f.name for f in holder.form.fields] == ["phone", "birth_date"]
