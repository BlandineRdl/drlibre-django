import dataclasses
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

from drlibre.booking.application.ports.inbound import (
    AgendaHour,
    AppointmentFile,
    AppointmentStatus,
    ClinicianDayView,
    ClinicianEntry,
    ClinicianPatient,
    ClinicianWeekView,
    DayCounts,
    HistoryActor,
    HistoryLine,
    RoomBooking,
    RoomLabel,
    RoomsDayView,
)
from drlibre.booking.domain.booking_rules import clinician_actions
from drlibre.interfaces.web.forms.portal import CancelForm
from drlibre.interfaces.web.forms.workspace import NotesForm
from drlibre.interfaces.web.presenters.workspace import (
    appointment_page,
    calendar_page,
    cancel_page,
    day_param,
    patients_page,
    rooms_page,
    today_page,
    workspace_nav,
)
from drlibre.scheduling.application.ports.inbound import FreeWeek, Slot
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page
from tests.builders_booking import existing_appointment
from tests.builders_scheduling import time_off

ZONE = "Europe/Paris"
MONDAY = date(2026, 11, 23)
# Monday 09:00 in Paris.
NINE = datetime(2026, 11, 23, 8, tzinfo=UTC)
CLINICIAN = Id()


def entry(
    start: datetime = NINE,
    status: AppointmentStatus = AppointmentStatus.BOOKED,
    *,
    room: str | None = "C101",
    name: str = "Ana Martin",
) -> ClinicianEntry:
    a = existing_appointment(
        patient_id=Id(),
        clinician_id=CLINICIAN,
        start=start,
        end=start + timedelta(minutes=30),
        status=status,
        reason="Douleur",
    )
    found = ClinicianEntry(
        appointment=a,
        patient_name=name,
        patient_phone="0612345678",
        patient_birth_date=date(1990, 5, 17),
        appointment_type="Consultation",
        type_colour="#336699",
        room=room,
    )
    return dataclasses.replace(found, actions=clinician_actions(a))


def day(*entries: ClinicianEntry, next_free: datetime | None = None) -> ClinicianDayView:
    zone = ZoneInfo(ZONE)
    groups = tuple(AgendaHour(e.appointment.start.astimezone(zone).hour, (e,)) for e in entries)
    counts = DayCounts(appointments=5, cancelled=1, completed=2, no_show=1)
    return ClinicianDayView(MONDAY, ZONE, groups, counts, next_free)


def file(e: ClinicianEntry, history: tuple[HistoryLine, ...] = ()) -> AppointmentFile:
    return AppointmentFile(entry=e, time_zone=ZONE, patient_age=36, history=history)


def week(slots: tuple[datetime, ...] = (NINE + timedelta(hours=2),)) -> FreeWeek:
    return FreeWeek(
        monday=MONDAY,
        previous_monday=None,
        next_monday=MONDAY + timedelta(days=7),
        time_zone=ZONE,
        slots=tuple(Slot(s, s + timedelta(minutes=30)) for s in slots),
    )


def test_the_day_names_its_time_zone_and_links_previous_today_and_next() -> None:
    """Story agenda du jour : liens précédent, suivant, aujourd'hui ; fuseau indiqué."""
    view = today_page(day(entry()))

    assert view.heading == "Agenda du Lundi 23/11/2026"
    assert view.time_zone == ZONE
    assert (view.nav.previous_url, view.nav.today_url, view.nav.next_url) == (
        "/workspace/?day=2026-11-22",
        "/workspace/",
        "/workspace/?day=2026-11-24",
    )


def test_an_unusable_date_in_the_address_falls_back_to_today() -> None:
    """Story agenda du jour : une date inutilisable dans l'adresse revient à aujourd'hui."""
    assert day_param("abc") is None
    assert day_param("0001-01-02") is None
    assert day_param("2026-11-23") == MONDAY


def test_the_tiles_count_appointments_cancelled_apart_completed_absent_and_next_free_slot() -> None:
    """Story agenda du jour : RDV, annulés à part, terminés, absents, prochain créneau libre."""
    free = today_page(day(entry(), next_free=NINE + timedelta(hours=6, minutes=30)))
    none = today_page(day(entry()))

    assert [(t.label, t.value) for t in free.tiles] == [
        ("RDV", "5"),
        ("Annulés", "1"),
        ("Terminés", "2"),
        ("Absents", "1"),
        ("Prochain créneau libre", "lun. 23/11 15:30"),
    ]
    assert none.tiles[-1].value == "—"


def test_appointments_are_grouped_by_hour_with_patient_type_room_and_status() -> None:
    """Story agenda du jour : RDV groupés par heure avec patient, type, salle et statut."""
    view = today_page(day(entry(), entry(NINE + timedelta(hours=1), room=None, name="Léo Roy")))

    (nine,), (ten,) = view.hours[0].rows, view.hours[1].rows
    assert [g.heading for g in view.hours] == ["09:00", "10:00"]
    assert (nine.time, nine.patient, nine.appointment_type, nine.room, nine.status) == (
        "09:00-09:30",
        "Ana Martin",
        "Consultation",
        "C101",
        "Réservé",
    )
    assert ten.room == "—"


def test_the_day_offers_only_the_actions_the_current_status_allows() -> None:
    """Story statut : l'agenda du jour ne propose que les actions permises par le statut."""
    booked, checked_in, completed, cancelled = (
        entry(),
        entry(status=AppointmentStatus.CHECKED_IN),
        entry(status=AppointmentStatus.COMPLETED),
        entry(status=AppointmentStatus.CANCELLED),
    )

    rows = [today_page(day(e)).hours[0].rows[0] for e in (booked, checked_in, completed, cancelled)]

    assert [[b.label for b in r.buttons] for r in rows] == [
        ["Arrivé", "Absent"],
        ["Terminé"],
        [],
        [],
    ]
    assert [bool(r.cancel_url) for r in rows] == [True, True, False, False]
    assert rows[0].buttons[0].url == f"/workspace/appointments/{booked.appointment.id}/check-in"
    assert rows[0].buttons[0].aria_label == "Arrivé : 09:00-09:30 Ana Martin"
    assert rows[3].status == "Annulé"
    assert [r.status_key for r in rows][-1] == "cancelled"


def test_the_week_shows_appointments_named_by_their_type_in_its_colour() -> None:
    """Story semaine : RDV actifs dans la couleur de leur type ; la couleur n'est pas seule."""
    booked = entry()
    view = calendar_page(ClinicianWeekView(MONDAY, ZONE, (booked,)), rules=(), time_offs=())

    nine = next(r for r in view.rows if r.time == "09:00")
    monday = nine.cells[0]
    assert (len(view.rows), view.rows[0].time, view.rows[-1].time) == (24, "07:00", "18:30")
    assert (monday.kind, monday.text, monday.colour) == ("appointment", "Consultation", "#336699")
    assert monday.hue_class == "hue-5"
    assert monday.url == f"/workspace/appointments/{booked.appointment.id}"
    assert view.time_zone == ZONE
    assert view.previous_url == "/workspace/calendar?week=2026-11-16"


def test_the_clinicians_time_off_appears_as_blocks_in_the_week() -> None:
    """Story semaine : les absences du praticien apparaissent en blocs."""
    off = time_off(CLINICIAN, NINE + timedelta(days=1), NINE + timedelta(days=1, hours=2))

    view = calendar_page(ClinicianWeekView(MONDAY, ZONE, ()), rules=(), time_offs=(off,))

    tuesday = [r.cells[1] for r in view.rows]
    blocked = [c for c in tuesday if c.kind == "time-off"]
    assert [c.text for c in blocked] == ["Absence"] * 4


def test_the_file_shows_patient_phone_age_time_type_room_reason_and_status() -> None:
    """Story fiche : nom, téléphone, âge, heure, type, salle, motif et statut."""
    view = appointment_page(file(entry()), week=None)

    assert [(f.label, f.value) for f in view.facts] == [
        ("Patient", "Ana Martin"),
        ("Téléphone", "0612345678"),
        ("Âge", "36 ans"),
        ("Horaire", "Lundi 23/11/2026, 09:00-09:30"),
        ("Type", "Consultation"),
        ("Salle", "C101"),
        ("Motif", "Douleur"),
        ("Statut", "Réservé"),
    ]


def test_the_history_lists_audit_entries_in_order_with_who_acted() -> None:
    """Story fiche : l'historique liste les entrées d'audit dans l'ordre chronologique."""
    history = (
        HistoryLine("booking.appointment_booked", HistoryActor.PATIENT, NINE - timedelta(days=3)),
        HistoryLine("booking.appointment_status_changed", HistoryActor.CLINICIAN, NINE),
    )

    view = appointment_page(file(entry(), history), week=None)

    assert [(h.at, h.action, h.actor) for h in view.history] == [
        ("20/11/2026 09:00", "RDV réservé", "Patient"),
        ("23/11/2026 09:00", "Statut modifié", "Praticien"),
    ]


def test_the_file_offers_the_week_strip_of_free_slots_only_when_movable() -> None:
    """Story déplace : le bandeau propose les créneaux libres ; seul un RDV BOOKED se déplace."""
    booked, checked_in = entry(), entry(status=AppointmentStatus.CHECKED_IN)

    movable = appointment_page(file(booked), week=week())
    fixed = appointment_page(file(checked_in), week=week())

    assert movable.strip is not None
    assert movable.strip.action == f"/workspace/appointments/{booked.appointment.id}/reschedule"
    assert movable.strip.days[0].slots[0].label == "11:00"
    assert movable.strip.next_url.endswith("/reschedule?week=2026-11-30")
    assert fixed.strip is None


def test_a_refused_move_is_explained_with_the_current_status_and_rules() -> None:
    """Story déplace : rule_violation outside_availability et invalid_transition, en ligne."""
    rule = DomainError(
        ErrorCode.RULE_VIOLATION,
        "Le déplacement enfreint une règle.",
        {"rules": ["outside_availability"]},
    )
    transition = DomainError(
        ErrorCode.INVALID_TRANSITION,
        "Ce rendez-vous ne permet pas ce changement.",
        {"status": "COMPLETED"},
    )

    by_rule = appointment_page(file(entry()), week=week(), refusal=rule)
    by_status = appointment_page(file(entry()), week=week(), refusal=transition)

    assert by_rule.reasons == ("ce créneau n'est pas libre",)
    assert by_status.refusal.endswith("Statut actuel : Terminé.")


def test_notes_are_posted_on_their_own_form_starting_from_the_saved_text() -> None:
    """Story notes : enregistrées depuis la fiche, à part ; un refus garde le texte saisi."""
    noted = entry()
    noted = dataclasses.replace(
        noted, appointment=dataclasses.replace(noted.appointment, clinical_notes="RAS")
    )
    typed = NotesForm({"clinical_notes": "x" * 5001})

    saved = appointment_page(file(noted), week=None)
    refused = appointment_page(file(noted), week=None, notes=typed)

    assert saved.notes.action == f"/workspace/appointments/{noted.appointment.id}/notes"
    assert saved.notes.form["clinical_notes"].value() == "RAS"
    assert refused.notes.form is typed


def test_cancelling_needs_a_reason_tied_to_its_field() -> None:
    """Story annule : le motif est obligatoire ; sans motif, invalid_input sur le champ."""
    booked = entry()

    view = cancel_page(file(booked), CancelForm({"reason": ""}))

    assert view.form.action == f"/workspace/appointments/{booked.appointment.id}/cancel"
    assert view.form.form.errors["reason"] == ["Ce champ est obligatoire."]
    assert view.form.cancel_url == f"/workspace/appointments/{booked.appointment.id}"


def test_the_navigation_marks_the_current_workspace_page() -> None:
    """§9 : la navigation du praticien marque la page courante."""
    links = workspace_nav("/workspace/appointments/abc")
    calendar = workspace_nav("/workspace/calendar")

    assert [link.label for link in links] == [
        "Aujourd'hui",
        "Calendrier",
        "Patients",
        "Salles",
        "Mes plages",
        "Mes absences",
    ]
    assert [link.label for link in links if link.current] == ["Aujourd'hui"]
    assert [link.label for link in calendar if link.current] == ["Calendrier"]


def patient(name: str, *, last: datetime | None, next_visit: datetime | None) -> ClinicianPatient:
    return ClinicianPatient(Id(), name, None, last, next_visit)


def test_each_patient_shows_phone_last_and_next_visit_in_the_hospital_zone() -> None:
    """Story patients : chaque patient montre son téléphone, sa dernière et prochaine visite."""
    seen = ClinicianPatient(Id(), "Ana Martin", "0612345678", NINE - timedelta(days=7), NINE)
    new = patient("Léo Roy", last=None, next_visit=None)

    view = patients_page(Page((seen, new), total=2, number=1), search="", time_zone=ZONE)

    assert [(r.name, r.phone, r.last_visit, r.next_visit) for r in view.rows] == [
        ("Ana Martin", "0612345678", "16/11/2026 09:00", "23/11/2026 09:00"),
        ("Léo Roy", "—", "—", "—"),
    ]
    assert (view.empty_text, view.previous_url, view.next_url) == ("", "", "")


def test_a_name_search_keeps_its_query_across_pages() -> None:
    """Story patients : une recherche par nom filtre la liste, paginée par 20."""
    rows = tuple(patient(f"Martin {n}", last=None, next_visit=None) for n in range(20))

    view = patients_page(Page(rows, total=25, number=1), search="mar", time_zone=ZONE)

    assert view.search == "mar"
    assert view.summary == "Page 1 sur 2"
    assert view.next_url == "/workspace/patients?q=mar&page=2"


def test_a_search_without_match_offers_a_reset_link() -> None:
    """Story patients : sans résultat, un état vide avec un lien pour tout afficher."""
    empty = patients_page(Page((), total=0, number=1), search="zz", time_zone=ZONE)
    none = patients_page(Page((), total=0, number=1), search="", time_zone=ZONE)

    assert (empty.empty_text, empty.reset_url) == (
        "Aucun patient ne correspond à « zz ».",
        "/workspace/patients",
    )
    assert (none.empty_text, none.reset_url) == ("Aucun patient pour l'instant.", "")


def test_the_rooms_timeline_names_own_patients_and_marks_others_occupied() -> None:
    """Story salles : 07:00 à 19:00 ; ses RDV nommés, ceux des autres « Occupied »."""
    room, other = RoomLabel(Id(), "C101"), RoomLabel(Id(), "C102")
    bookings = (
        RoomBooking(room.id, NINE, NINE + timedelta(minutes=30), "Ana Martin"),
        RoomBooking(room.id, NINE + timedelta(hours=1), NINE + timedelta(hours=2), None),
    )

    view = rooms_page(RoomsDayView(MONDAY, ZONE, (room, other), bookings))

    cells = dict(zip(view.times, view.rows[0].cells, strict=True))
    assert (len(view.times), view.times[0], view.times[-1]) == (24, "07:00", "18:30")
    assert [r.name for r in view.rows] == ["C101", "C102"]
    assert (cells["09:00"].text, cells["09:00"].english) == ("Ana Martin", False)
    assert cells["09:30"].text == ""
    assert [(cells[t].text, cells[t].english) for t in ("10:00", "10:30")] == [
        ("Occupied", True),
        ("Occupied", True),
    ]
    assert all(c.text == "" for c in view.rows[1].cells)
    assert view.heading == "Salles du Lundi 23/11/2026"
    assert view.time_zone == ZONE
    assert view.nav.next_url == "/workspace/rooms?day=2026-11-24"


def test_a_department_without_active_room_says_so() -> None:
    """Story salles : la frise liste les salles actives du département, ici aucune."""
    view = rooms_page(RoomsDayView(MONDAY, ZONE, (), ()))

    assert (view.rows, view.empty_text) == ((), "Aucune salle active dans votre département.")
