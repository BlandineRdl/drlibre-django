from uuid import UUID

from django.http import HttpRequest
from ninja import Query, Router, Schema
from pydantic import AwareDatetime, ConfigDict

from drlibre.bootstrap.container import container
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.validation import invalid_field

router = Router(tags=["slots"])


class SlotsQuery(Schema):
    model_config = ConfigDict(extra="forbid")

    type: UUID
    clinician: UUID | None = None
    start: AwareDatetime
    end: AwareDatetime


class SlotOut(Schema):
    start: str
    end: str


class SlotsOut(Schema):
    slots: list[SlotOut]


@router.get("/slots", response=SlotsOut)
def free_slots(request: HttpRequest, query: Query[SlotsQuery]) -> SlotsOut:
    # Ninja drops unknown query keys before the schema, so extra="forbid" alone misses them.
    unknown = sorted(set(request.GET) - set(SlotsQuery.model_fields))
    if unknown:
        raise invalid_field(unknown[0], "Paramètre inconnu.")
    found = container().find_free_slots.execute(
        appointment_type_id=Id(query.type),
        clinician_id=Id(query.clinician) if query.clinician else None,
        start=query.start,
        end=query.end,
    )
    return SlotsOut(
        slots=[SlotOut(start=s.start.isoformat(), end=s.end.isoformat()) for s in found]
    )
