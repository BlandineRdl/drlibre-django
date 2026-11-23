from drlibre.booking.application.ports.inbound import MAX_CLINICAL_NOTES
from drlibre.interfaces.web.forms.workspace import NotesForm, RuleForm, TimeOffForm
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from tests.markup import attributes

RULE = {"weekday": "1", "start": "09:00", "end": "12:00", "step_minutes": "15"}


def test_notes_beyond_the_limit_are_refused_and_focused() -> None:
    """Story notes : au-delà de la limite, refus sur le champ."""
    form = NotesForm({"clinical_notes": "x" * (MAX_CLINICAL_NOTES + 1)})

    assert not form.is_valid()
    notes = attributes(form.render(), "field-clinical_notes")
    assert (notes["aria-invalid"], "autofocus" in notes) == ("true", True)
    assert NotesForm({"clinical_notes": ""}).is_valid()


def test_a_rule_names_the_clinician_zone_and_offers_only_their_rooms() -> None:
    """Story plages : heures locales du fuseau de l'hôpital, salle facultative."""
    room = ("r1", "Salle 1")
    form = RuleForm(RULE, time_zone="Europe/Paris", rooms=(room,))

    assert form.is_valid()
    html = form.render()
    assert "HH:MM, heure locale (Europe/Paris)." in html
    assert "Salle 1" in html
    assert not RuleForm({**RULE, "room_id": "other"}, time_zone="UTC", rooms=(room,)).is_valid()


def test_an_overlapping_rule_refused_by_the_use_case_focuses_its_start() -> None:
    """Story plages : deux plages du même jour ne se chevauchent pas ; le refus le dit."""
    form = RuleForm(RULE, time_zone="Europe/Paris", rooms=())
    assert form.is_valid()
    fields = [{"field": "start", "message": "Chevauche la plage Lundi 09:00-12:00."}]

    form.refuse(DomainError(ErrorCode.INVALID_INPUT, "Corrigez.", {"fields": fields}))

    start = attributes(form.render(), "field-start")
    assert (start["aria-invalid"], "autofocus" in start, start["value"]) == ("true", True, "09:00")


def test_a_re_rendered_time_off_keeps_the_value_a_datetime_input_reads() -> None:
    """Story absences : début et fin en date et heure locales."""
    form = TimeOffForm({"start": "2026-11-23T09:00", "end": ""}, time_zone="Europe/Paris")

    assert not form.is_valid()
    html = form.render()
    assert list(form.errors) == ["end"]
    assert attributes(html, "field-start")["value"] == "2026-11-23T09:00"
    assert "Date et heure locales (Europe/Paris)." in html


def test_a_time_off_typed_in_the_hospital_zone_is_left_to_the_use_case() -> None:
    """Story absences : l'heure est lue dans le fuseau de l'hôpital, pas celui du serveur."""
    # 02:30 on 25 Oct 2026 happens twice in Europe/Paris, once in America/Montreal.
    fields = {"start": "2026-10-25T02:30", "end": "2026-10-25T03:30"}
    form = TimeOffForm(fields, time_zone="America/Montreal")

    assert form.is_valid()
    assert (form.cleaned_data["start"], form.cleaned_data["end"]) == (
        fields["start"],
        fields["end"],
    )
