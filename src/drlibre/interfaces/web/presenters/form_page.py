from dataclasses import dataclass

from drlibre.interfaces.web.forms.base import WebForm


@dataclass(frozen=True, slots=True)
class FormPage:
    """A bound form with where it posts, its button and the way back."""

    title: str
    action: str
    submit_label: str
    form: WebForm
    cancel_url: str = ""
    cancel_label: str = "Annuler"
    submit_class: str = ""
