from datetime import UTC, date, datetime, time

from drlibre.interfaces.web.presenters.availability import (
    rule_values,
    rules_view,
    time_offs_view,
    week_start,
    week_view,
    weekly_summary,
)
from drlibre.shared_kernel.ids import Id
from tests.builders_scheduling import rule, time_off

CLINICIAN = Id()


def test_summary_lists_weekdays_monday_first_with_local_ranges() -> None:
    """Story résumé hebdomadaire : résumé des plages en heure locale de l'hôpital."""
    rules = (
        rule(CLINICIAN, weekday=0, start=time(8), end=time(9)),
        rule(CLINICIAN, weekday=1, start=time(14), end=time(17)),
        rule(CLINICIAN, weekday=1, start=time(9), end=time(12)),
    )

    assert weekly_summary(rules) == "Lun 09:00-12:00, 14:00-17:00 · Dim 08:00-09:00"
    assert weekly_summary(()) == "Aucune plage"


def test_rule_list_names_the_time_zone_and_offers_edit_and_delete() -> None:
    """Story plages : la page nomme le fuseau ; la suppression passe par une confirmation."""
    room = Id()
    saved = rule(CLINICIAN, weekday=2, start=time(9), end=time(12), room_id=room)

    view = rules_view((saved,), time_zone="America/Montreal", room_labels={room: "Salle 1"})

    (row,) = view.rows
    assert view.time_zone == "America/Montreal"
    assert (row.day, row.hours, row.step, row.room) == ("Mardi", "09:00-12:00", "15 min", "Salle 1")
    assert row.delete_url == f"/workspace/availability/{saved.id}/delete"


def test_rule_edit_form_starts_from_local_hours() -> None:
    saved = rule(CLINICIAN, weekday=1, start=time(9, 5), end=time(12))

    assert rule_values(saved) == {
        "weekday": "1",
        "start": "09:05",
        "end": "12:00",
        "step_minutes": "15",
        "room_id": "",
    }


def test_time_off_is_shown_in_the_hospital_local_time() -> None:
    """Story absences : début et fin affichés en heure locale de l'hôpital."""
    off = time_off(
        CLINICIAN, datetime(2026, 12, 1, 14, tzinfo=UTC), datetime(2026, 12, 1, 15, tzinfo=UTC)
    )

    (row,) = time_offs_view((off,), time_zone="America/Montreal").rows

    assert (row.start, row.end, row.reason) == ("01/12/2026 09:00", "01/12/2026 10:00", "Congés")


def test_a_bad_or_missing_week_falls_back_to_this_week_starting_monday() -> None:
    today = date(2026, 11, 20)

    assert week_start("2026-11-26", today=today) == date(2026, 11, 23)
    assert week_start("abc", today=today) == date(2026, 11, 16)
    assert week_start(None, today=today) == date(2026, 11, 16)


def test_week_grid_labels_availability_and_time_off_in_text_from_7_to_19() -> None:
    """Story calendrier : heures dans le fuseau de l'hôpital ; cellules libellées en texte."""
    rules = (rule(CLINICIAN, weekday=1, start=time(9), end=time(10)),)
    # 15:00 UTC is 10:00 in Montreal on 23 November.
    offs = (
        time_off(
            CLINICIAN,
            datetime(2026, 11, 23, 14, 30, tzinfo=UTC),
            datetime(2026, 11, 23, 15, 30, tzinfo=UTC),
        ),
    )

    view = week_view(
        clinician="Dr A",
        time_zone="America/Montreal",
        monday=date(2026, 11, 23),
        rules=rules,
        time_offs=offs,
        base_url="/console/clinicians/x/week",
    )

    monday = {row.time: row.cells[0].text for row in view.rows}
    assert (view.rows[0].time, view.rows[-1].time, len(view.rows)) == ("07:00", "18:30", 24)
    assert [t for t, text in monday.items() if text] == ["09:00", "09:30", "10:00"]
    assert (monday["09:00"], monday["09:30"], monday["10:00"]) == (
        "Disponible",
        "Absence",
        "Absence",
    )
    assert view.days[0].short == "Lun 23/11"
    assert view.previous_url.endswith("?week=2026-11-16")
    assert view.next_url.endswith("?week=2026-11-30")
