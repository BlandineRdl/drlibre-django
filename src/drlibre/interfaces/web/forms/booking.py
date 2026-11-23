from django import forms

from drlibre.booking.application.ports.inbound import MAX_BOOKING_REASON, MAX_FULL_NAME, MAX_PHONE
from drlibre.interfaces.web.forms.base import TelInput, WebForm
from drlibre.shared_kernel.booking_policy import CODE_LIFETIME


class DetailsForm(WebForm):
    full_name = forms.CharField(
        label="Nom complet",
        max_length=MAX_FULL_NAME,
        widget=forms.TextInput({"autocomplete": "name"}),
    )
    birth_date = forms.DateField(
        label="Date de naissance",
        help_text="Format jour/mois/année selon votre navigateur.",
        widget=forms.DateInput({"type": "date", "autocomplete": "bday"}, format="%Y-%m-%d"),
    )
    email = forms.EmailField(label="Email", widget=forms.EmailInput({"autocomplete": "email"}))
    phone = forms.CharField(
        label="Téléphone",
        required=False,
        max_length=MAX_PHONE,
        widget=TelInput({"autocomplete": "tel"}),
    )
    reason = forms.CharField(
        label="Motif",
        required=False,
        max_length=MAX_BOOKING_REASON,
        widget=forms.Textarea({"rows": 3}),
    )
    # Not required here: the use case refuses unaccepted terms with its own message.
    accepted_terms = forms.BooleanField(
        label="J'accepte les conditions et la notice de confidentialité", required=False
    )


class CodeForm(WebForm):
    code = forms.CharField(
        label="Code reçu par email",
        help_text=f"6 chiffres, valables {int(CODE_LIFETIME.total_seconds() // 60)} minutes.",
        widget=forms.TextInput({"autocomplete": "one-time-code"}),
    )
