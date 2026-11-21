from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.scheduling.application.ports.inbound import DeleteAvailabilityRule, RefreshSlots
from drlibre.scheduling.application.ports.outbound import AvailabilityRules, SchedulingDirectory
from drlibre.scheduling.application.use_cases.clinician_writes import ClinicianWrites
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class DeleteAvailabilityRuleUseCase(DeleteAvailabilityRule):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        directory: SchedulingDirectory,
        rules: AvailabilityRules,
        refresh: RefreshSlots,
    ) -> None:
        self._rules = rules
        self._writes = ClinicianWrites(
            clock=clock,
            uow=uow,
            audit=audit,
            directory=directory,
            refresh=refresh,
            entity_type="availability_rule",
        )

    def execute(self, *, actor: Id, rule_id: Id) -> None:
        clinician = self._writes.caller(actor)
        rule = self._writes.owned(self._rules.get(rule_id), rule_id, clinician)
        self._writes.commit(
            actor=actor,
            clinician=clinician,
            action="deleted",
            entity_id=rule.id,
            metadata={"weekday": rule.weekday},
            write=lambda: self._rules.delete(rule.id),
        )
