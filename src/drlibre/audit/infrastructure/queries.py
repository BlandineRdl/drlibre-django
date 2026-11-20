from drlibre.audit.application.ports.inbound import AuditQueries
from drlibre.audit.infrastructure.django.models import AuditEntryRecord
from drlibre.shared_kernel.ids import Id


class DjangoAuditQueries(AuditQueries):
    def has_acted(self, actor: Id) -> bool:
        return AuditEntryRecord.objects.filter(actor_id=actor.value).exists()
