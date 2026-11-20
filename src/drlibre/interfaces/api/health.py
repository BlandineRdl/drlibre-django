from datetime import datetime

from django.http import HttpRequest
from ninja import Router, Schema, Status

from drlibre.bootstrap.container import container

router = Router(tags=["health"])


class HealthOut(Schema):
    status: str
    database: str
    checked_at: datetime


@router.get("/health", response={200: HealthOut, 503: HealthOut}, auth=None)
def health(request: HttpRequest) -> Status[HealthOut]:
    report = container().check_health.execute()
    body = HealthOut(
        status=report.status.value, database=report.database.value, checked_at=report.checked_at
    )
    return Status(200 if report.is_healthy else 503, body)
