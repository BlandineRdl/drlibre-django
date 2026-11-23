from typing import Any

from django import forms

from drlibre.interfaces.web.forms.base import TelInput, WebForm, with_placeholder
from drlibre.interfaces.web.forms.portal import WaitlistJoinForm
from drlibre.interfaces.web.presenters.staff import ROLE_LABELS


def _text(label: str, *, autocomplete: str = "", **kwargs: Any) -> forms.CharField:
    attrs = {"autocomplete": autocomplete} if autocomplete else {}
    return forms.CharField(label=label, widget=forms.TextInput(attrs), **kwargs)


def _description() -> forms.CharField:
    return forms.CharField(label="Description", required=False, widget=forms.Textarea)


def _name() -> forms.CharField:
    return forms.CharField(label="Nom")


def _code() -> forms.CharField:
    return forms.CharField(
        label="Code", help_text="Unique : lettres, chiffres, tirets ; enregistré en majuscules."
    )


def _flag(label: str) -> forms.BooleanField:
    return forms.BooleanField(label=label, required=False)


class HospitalForm(WebForm):
    name = _name()
    code = _code()
    description = _description()
    street = _text("Adresse", autocomplete="street-address")
    postal_code = _text("Code postal", autocomplete="postal-code")
    city = _text("Ville", autocomplete="address-level2")
    country = _text("Pays", autocomplete="country-name")
    phone = forms.CharField(label="Téléphone", widget=TelInput({"autocomplete": "tel"}))
    time_zone = forms.CharField(
        label="Fuseau horaire", help_text="Nom IANA, par exemple Europe/Paris."
    )
    latitude = forms.CharField(label="Latitude", required=False, help_text="Entre -90 et 90.")
    longitude = forms.CharField(label="Longitude", required=False, help_text="Entre -180 et 180.")
    active = _flag("Actif")


class SpecialtyForm(WebForm):
    name = _name()
    code = _code()
    active = _flag("Actif")


class DepartmentForm(WebForm):
    hospital_id = forms.ChoiceField(label="Hôpital")
    name = _name()
    code = _code()
    description = _description()


class RoomForm(WebForm):
    department_id = forms.ChoiceField(label="Département")
    name = _name()
    code = _code()
    floor = forms.CharField(label="Étage")
    capacity = forms.IntegerField(label="Capacité", help_text="Au moins 1.")
    equipment = forms.CharField(
        label="Équipements", required=False, help_text="Séparés par des virgules."
    )
    active = _flag("Actif")


class AppointmentTypeForm(WebForm):
    department_id = forms.ChoiceField(label="Département")
    name = _name()
    code = _code()
    duration_minutes = forms.IntegerField(label="Durée en minutes", help_text="Au moins 1.")
    buffer_minutes = forms.IntegerField(
        label="Battement après la visite, en minutes", help_text="0 ou plus."
    )
    colour = forms.CharField(label="Couleur", help_text="Format #RRGGBB, par exemple #336699.")
    needs_room = _flag("Nécessite une salle")
    bookable_online = _flag("Réservable en ligne")
    active = _flag("Actif")


class UserForm(WebForm):
    full_name = _text("Nom complet", autocomplete="name")
    email = forms.EmailField(label="Email", help_text="Unique, enregistré en minuscules.")
    role = forms.ChoiceField(
        label="Rôle", choices=with_placeholder((r.value, label) for r, label in ROLE_LABELS.items())
    )
    active = _flag("Actif")
    temporary_password = forms.CharField(
        label="Mot de passe temporaire",
        strip=False,
        help_text="De 10 à 72 caractères ; la personne le changera à sa première connexion.",
        widget=forms.PasswordInput({"autocomplete": "new-password"}),
    )

    def __init__(self, *args: Any, creating: bool, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not creating:
            del self.fields["temporary_password"]


class ClinicianProfileForm(WebForm):
    user_id = forms.ChoiceField(label="Praticien")
    department_id = forms.ChoiceField(label="Département")
    specialty_id = forms.ChoiceField(label="Spécialité")
    title = forms.CharField(
        label="Titre", help_text="Affiché publiquement, par exemple Dr Ana Bel."
    )
    bio = forms.CharField(label="Bio", required=False, widget=forms.Textarea)
    default_room_id = forms.ChoiceField(
        label="Salle par défaut",
        required=False,
        help_text="Une salle active du département choisi.",
    )
    weight = forms.IntegerField(
        label="Poids round robin", required=False, help_text="1 par défaut."
    )

    def __init__(self, *args: Any, attaching: bool, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not attaching:
            del self.fields["user_id"]


class WaitlistAddForm(WaitlistJoinForm):
    field_order = ("patient_email",)

    patient_email = forms.EmailField(
        label="Email du patient", widget=forms.EmailInput({"autocomplete": "off"})
    )
