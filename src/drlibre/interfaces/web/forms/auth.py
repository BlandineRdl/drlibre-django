from django import forms

from drlibre.identity.application.ports.inbound import PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH
from drlibre.interfaces.web.forms.base import WebForm

PASSWORD_LENGTHS = f"De {PASSWORD_MIN_LENGTH} à {PASSWORD_MAX_LENGTH} caractères"


class SignInForm(WebForm):
    email = forms.EmailField(label="Email", widget=forms.EmailInput({"autocomplete": "username"}))
    password = forms.CharField(
        label="Mot de passe",
        strip=False,
        widget=forms.PasswordInput({"autocomplete": "current-password"}),
    )


class LinkRequestForm(WebForm):
    link_email = forms.EmailField(label="Email", widget=forms.EmailInput({"autocomplete": "email"}))


class PasswordChangeForm(WebForm):
    current_password = forms.CharField(
        label="Mot de passe actuel",
        strip=False,
        widget=forms.PasswordInput({"autocomplete": "current-password"}),
    )
    new_password = forms.CharField(
        label="Nouveau mot de passe",
        strip=False,
        min_length=PASSWORD_MIN_LENGTH,
        max_length=PASSWORD_MAX_LENGTH,
        help_text=f"{PASSWORD_LENGTHS}, différent de l'actuel.",
        widget=forms.PasswordInput({"autocomplete": "new-password"}),
    )
