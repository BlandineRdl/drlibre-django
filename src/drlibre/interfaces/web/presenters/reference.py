import dataclasses
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.pagination import Page, PageRequest

_DONE = {
    "created": "L'élément a été créé.",
    "updated": "Les modifications ont été enregistrées.",
    "deleted": "L'élément a été supprimé.",
}


@dataclass(frozen=True, slots=True)
class Column:
    label: str
    cell: Callable[[Any], str]


@dataclass(frozen=True, slots=True)
class RowView:
    label: str
    cells: tuple[str, ...]
    edit_url: str
    delete_url: str


@dataclass(frozen=True, slots=True)
class ListView:
    title: str
    base_url: str
    headers: tuple[str, ...]
    rows: tuple[RowView, ...]
    total: int
    search: str
    number: int
    pages: int
    previous_url: str
    next_url: str
    status: str

    @property
    def summary(self) -> str:
        noun = "résultat" if self.total == 1 else "résultats"
        return f"{self.total} {noun} · page {self.number} sur {self.pages}"


@dataclass(frozen=True, slots=True)
class DependentView:
    kind: str
    label: str


@dataclass(frozen=True, slots=True)
class ConfirmView:
    title: str
    action: str
    cancel_url: str
    refusal: str
    dependents: tuple[DependentView, ...]


_KINDS = {
    "department": "Département",
    "room": "Salle",
    "appointment_type": "Type de RDV",
    "clinician": "Praticien",
    "appointment": "Rendez-vous",
    "availability_rule": "Disponibilité",
    "waitlist_entry": "Liste d'attente",
}


def yes_no(value: bool) -> str:
    return "Oui" if value else "Non"


def list_view(
    *,
    title: str,
    base_url: str,
    columns: tuple[Column, ...],
    page: Page[Any],
    request: PageRequest,
    label: Callable[[Any], str],
    done: str | None = None,
    deletable: bool = True,
) -> ListView:
    def url(number: int) -> str:
        query = {"page": number, **({"search": request.search} if request.search else {})}
        return f"{base_url}?{urlencode(query)}"

    rows = tuple(
        RowView(
            label=label(record),
            cells=tuple(column.cell(record) for column in columns),
            edit_url=f"{base_url}{record.id}/edit",
            delete_url=f"{base_url}{record.id}/delete" if deletable else "",
        )
        for record in page.items
    )
    return ListView(
        title=title,
        base_url=base_url,
        headers=tuple(column.label for column in columns),
        rows=rows,
        total=page.total,
        search=request.search,
        number=page.number,
        pages=page.pages,
        previous_url=url(page.number - 1) if page.has_previous else "",
        next_url=url(page.number + 1) if page.has_next else "",
        status=_DONE.get(done or "", ""),
    )


def record_values(record: Any) -> dict[str, str]:
    """A stored record as the raw text its edit form starts from."""
    values: dict[str, str] = {}
    for field in dataclasses.fields(record):
        value = getattr(record, field.name)
        if isinstance(value, bool):
            values[field.name] = "on" if value else ""
        elif isinstance(value, tuple):
            values[field.name] = ", ".join(str(item) for item in value)
        elif value is None:
            values[field.name] = ""
        else:
            values[field.name] = str(value)
    return values


def confirm_view(
    *, label: str, action: str, cancel_url: str, error: DomainError | None = None
) -> ConfirmView:
    refused = error is not None and error.code is ErrorCode.HAS_DEPENDENTS
    dependents = tuple(
        DependentView(_KINDS.get(item["kind"], item["kind"]), item["label"])
        for item in (error.details.get("dependents", []) if error and refused else [])
    )
    return ConfirmView(
        title=f"Supprimer « {label} » ?",
        action=action,
        cancel_url=cancel_url,
        refusal=error.message if error else "",
        dependents=dependents,
    )


def labels_by_id(options: tuple[Any, ...]) -> Mapping[Id, str]:
    return {option.id: option.label for option in options}
