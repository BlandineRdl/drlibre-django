"""The readable summary (`text`) FHIR R4 asks of every resource (dom-6), from its own elements."""

from collections.abc import Mapping
from html import escape
from typing import Any

XHTML = "http://www.w3.org/1999/xhtml"
_LABELS = ("display", "text", "contentString", "diagnostics", "title", "name", "reference")
# Elements a reader recognises a resource by, in display order; clinical notes stay out.
_SHOWN = (
    "title",
    "name",
    "description",
    "status",
    "active",
    "participantStatus",
    "action",
    "type",
    "subtype",
    "specialty",
    "serviceType",
    "category",
    "code",
    "birthDate",
    "start",
    "end",
    "recorded",
    "sent",
    "practitioner",
    "providedBy",
    "partOf",
    "actor",
    "schedule",
    "appointment",
    "recipient",
    "payload",
    "participant",
    "cancelationReason",
    "issue",
)


def _readable(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in _LABELS:
            if key in value:
                return _readable(value[key])
        nested = [v for k, v in value.items() if k not in ("system", "url")]
        return ", ".join(r for r in map(_readable, nested) if r)
    if isinstance(value, list | tuple):
        return ", ".join(r for r in map(_readable, value) if r)
    if isinstance(value, bool):
        return "oui" if value else "non"
    return "" if value is None else str(value)


def narrative(resource: Mapping[str, Any]) -> dict[str, str]:
    """A generated `text`: the resource type, then one line per element a reader recognises."""
    lines = [
        f"<li><b>{escape(key)}</b> : {escape(shown)}</li>"
        for key in _SHOWN
        if key in resource and (shown := _readable(resource[key]))
    ]
    heading = escape(str(resource.get("resourceType", "")))
    body = f"<ul>{''.join(lines)}</ul>" if lines else ""
    return {"status": "generated", "div": f'<div xmlns="{XHTML}"><p>{heading}</p>{body}</div>'}
