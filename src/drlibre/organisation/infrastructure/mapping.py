import dataclasses
from typing import Any

from django.db import models

from drlibre.shared_kernel.ids import Id


def to_columns(record: Any) -> dict[str, Any]:
    """Dataclass record → model columns: ids become UUIDs, tuples become JSON lists."""
    columns: dict[str, Any] = {}
    for field in dataclasses.fields(record):
        value = getattr(record, field.name)
        if isinstance(value, Id):
            value = value.value
        elif isinstance(value, tuple):
            value = list(value)
        columns[field.name] = value
    return columns


def from_row[T](entity: type[T], row: models.Model) -> T:
    """Model row → dataclass record, by matching field names."""
    values: dict[str, Any] = {}
    for field in dataclasses.fields(entity):  # pyrefly: ignore[bad-argument-type]
        value = getattr(row, field.name)
        if (field.name == "id" or field.name.endswith("_id")) and value is not None:
            value = Id(value)
        elif isinstance(value, list):
            value = tuple(value)
        values[field.name] = value
    return entity(**values)
