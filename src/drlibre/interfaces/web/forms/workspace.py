from collections.abc import Iterable
from typing import Any

from django import forms

from drlibre.booking.application.ports.inbound import MAX_CLINICAL_NOTES
from drlibre.interfaces.web.forms.base import WebForm, with_placeholder
from drlibre.interfaces.web.presenters.availability import WEEK_ORDER
from drlibre.scheduling.application.ports.inbound import WEEKDAYS


class NotesForm(WebForm):
    clinical_notes = forms.CharField(
        label="Notes cliniques",
        required=False,
        max_length=MAX_CLINICAL_NOTES,
        help_text=f"{MAX_CLINICAL_NOTES} caractères au plus ; visibles par vous seul.",
        widget=forms.Textarea({"rows": 3}),
    )


class RuleForm(WebForm):
    weekday = forms.ChoiceField(
        label="Jour", choices=with_placeholder((str(d), WEEKDAYS[d]) for d in WEEK_ORDER)
    )
    start = forms.TimeField(label="Début", widget=forms.TimeInput({"type": "time"}, format="%H:%M"))
    end = forms.TimeField(label="Fin", widget=forms.TimeInput({"type": "time"}, format="%H:%M"))
    step_minutes = forms.IntegerField(label="Pas en minutes", help_text="De 5 à 240 minutes.")
    room_id = forms.ChoiceField(
        label="Salle", required=False, help_text="Une salle active de votre département."
    )

    def __init__(
        self, *args: Any, time_zone: str, rooms: Iterable[tuple[str, str]], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        local = f"HH:MM, heure locale ({time_zone})."
        self.fields["start"].help_text = local
        self.fields["end"].help_text = f"Après le début ; {local}"
        self.offer("room_id", rooms)


class TimeOffForm(WebForm):
    start = forms.DateTimeField(
        label="Début",
        widget=forms.DateTimeInput({"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )
    end = forms.DateTimeField(
        label="Fin",
        widget=forms.DateTimeInput({"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
    )
    reason = forms.CharField(
        label="Motif",
        required=False,
        max_length=200,
        help_text="200 caractères au plus.",
        widget=forms.Textarea({"rows": 3}),
    )

    def __init__(self, *args: Any, time_zone: str, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        local = f"Date et heure locales ({time_zone})."
        self.fields["start"].help_text = local
        self.fields["end"].help_text = f"Après le début ; {local}"
