from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog


class AuditLogUnavailableError(RuntimeError):
    pass


class InMemoryAuditLog(AuditLog):
    def __init__(self, *, failing: bool = False) -> None:
        self.entries: list[AuditEntry] = []
        self.failing = failing

    def record(self, entry: AuditEntry) -> None:
        if self.failing:
            raise AuditLogUnavailableError("audit log unavailable")
        self.entries.append(entry)

    def actions(self) -> list[str]:
        return [entry.action for entry in self.entries]
