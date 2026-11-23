from collections.abc import Iterable
from typing import Any

from django import forms

from drlibre.booking.application.ports.inbound import MAX_CANCELLATION_REASON
from drlibre.interfaces.web.forms.base import TelInput, WebForm
from drlibre.shared_kernel.ids import Id

PICK_A_DATE = {"required": "Saisissez une date.", "invalid": "Saisissez une date."}


def date_input() -> forms.DateInput:
    return forms.DateInput({"type": "date"}, format="%Y-%m-%d")


class CancelForm(WebForm):
    reason = forms.CharField(
        label="Motif de l'annulation",
        max_length=MAX_CANCELLATION_REASON,
        help_text=f"{MAX_CANCELLATION_REASON} caractères au plus.",
        widget=forms.Textarea({"rows": 3}),
    )


class ProfileForm(WebForm):
    phone = forms.CharField(
        label="Téléphone",
        required=False,
        help_text=(
            "De 7 à 20 caractères : chiffres, espaces et + ( ) -. Laisser vide pour l'effacer."
        ),
        widget=TelInput({"autocomplete": "tel"}),
    )
    birth_date = forms.DateField(
        label="Date de naissance",
        required=False,
        help_text="Laisser vide pour l'effacer.",
        widget=forms.DateInput({"type": "date", "autocomplete": "bday"}, format="%Y-%m-%d"),
    )


class WaitlistJoinForm(WebForm):
    appointment_type_id = forms.TypedChoiceField(label="Type de RDV", coerce=Id.parse)
    clinician_id = forms.TypedChoiceField(
        label="Praticien préféré", coerce=Id.parse, required=False, empty_value=None
    )
    from_date = forms.DateField(
        label="Du",
        help_text="Premier jour où vous êtes disponible.",
        error_messages=PICK_A_DATE,
        widget=date_input(),
    )
    to_date = forms.DateField(
        label="Au",
        help_text="Dernier jour, inclus.",
        error_messages=PICK_A_DATE,
        widget=date_input(),
    )

    def __init__(
        self,
        *args: Any,
        types: Iterable[tuple[str, str]],
        clinicians: Iterable[tuple[str, str]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.offer("appointment_type_id", types)
        self.offer("clinician_id", clinicians)
