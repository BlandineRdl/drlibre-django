from django.http import HttpRequest
from ninja import Router, Schema

from drlibre.bootstrap.container import container
from drlibre.interfaces.web.auth import current_identity

router = Router(tags=["jobs"])


class RemindersOut(Schema):
    count: int


@router.post("/jobs/reminders", response=RemindersOut, auth=None)
def run_reminders(request: HttpRequest) -> RemindersOut:
    identity = current_identity(request)
    return RemindersOut(count=container().run_reminders.execute(actor_id=identity.user_id))
