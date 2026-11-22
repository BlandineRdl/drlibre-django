"""A written `Schedule` as the `fields` of the workspace's availability rule screen."""

from drlibre.interfaces.fhir.mappers.directory import DAYS, extension_url
from drlibre.interfaces.fhir.mappers.directory_writes import Fields, reference_id
from drlibre.interfaces.fhir.schemas.common import Extension
from drlibre.interfaces.fhir.schemas.directory import Schedule


def _hours(resource: Schedule) -> dict[str, Extension]:
    found = [e for e in resource.extension or () if e.url == extension_url("availability")]
    return {e.url: e for e in (found[0].extension or ())} if found else {}


def _clock(found: Extension | None) -> str:
    """A FHIR time as the screen's HH:MM; any other shape goes on for the rule to refuse."""
    raw = (found.value_time if found else None) or ""
    return raw[:5] if len(raw) == 8 and raw.endswith(":00") else raw


def _weekday(found: Extension | None) -> str:
    code = (found.value_code if found else None) or ""
    return str(DAYS.index(code)) if code in DAYS else code


def _actor(resource: Schedule, resource_type: str) -> str:
    return next((i for a in resource.actor if (i := reference_id(a, resource_type))), "")


def practitioner_of(resource: Schedule) -> str:
    return _actor(resource, "Practitioner")


def schedule_fields(resource: Schedule) -> Fields:
    hours = _hours(resource)
    step = hours["step-minutes"].value_integer if "step-minutes" in hours else None
    return {
        "weekday": _weekday(hours.get("weekday")),
        "start": _clock(hours.get("start")),
        "end": _clock(hours.get("end")),
        "step_minutes": "" if step is None else str(step),
        "room_id": _actor(resource, "Location"),
    }


def schedule_paths(resource: Schedule) -> dict[str, object]:
    """What an update may not change: its practitioner and its horizon, set as on the screen."""
    horizon = resource.planning_horizon
    return {
        "Schedule.actor.practitioner": practitioner_of(resource),
        "Schedule.planningHorizon": horizon.model_dump() if horizon else None,
    }
