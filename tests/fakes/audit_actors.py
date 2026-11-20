from drlibre.identity.application.ports.outbound import AuditActors
from drlibre.shared_kernel.ids import Id
from tests.fakes.audit_log import InMemoryAuditLog


class InMemoryAuditActors(AuditActors):
    def __init__(self, log: InMemoryAuditLog) -> None:
        self.log = log

    def has_acted(self, user_id: Id) -> bool:
        return any(entry.actor == user_id for entry in self.log.entries)
