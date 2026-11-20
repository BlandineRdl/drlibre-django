from drlibre.audit.application.ports.inbound import AuditQueries
from drlibre.identity.application.ports.outbound import AuditActors
from drlibre.shared_kernel.ids import Id


class AuditLogActors(AuditActors):
    """Asks the audit context, through its inbound port, whether the user ever acted."""

    def __init__(self, queries: AuditQueries) -> None:
        self._queries = queries

    def has_acted(self, user_id: Id) -> bool:
        return self._queries.has_acted(user_id)
