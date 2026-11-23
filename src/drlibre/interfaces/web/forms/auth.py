from django import forms

from drlibre.interfaces.web.forms.base import WebForm


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
        min_length=10,
        max_length=72,
        help_text="De 10 à 72 caractères, différent de l'actuel.",
        widget=forms.PasswordInput({"autocomplete": "new-password"}),
    )
