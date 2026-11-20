from collections.abc import Mapping
from zoneinfo import ZoneInfo

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.scheduling.application.ports.inbound import RefreshSlots, SaveAvailabilityRule
from drlibre.scheduling.application.ports.outbound import (
    AvailabilityRules,
    Clinician,
    SchedulingDirectory,
)
from drlibre.scheduling.application.use_cases.clinician_writes import ClinicianWrites
from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import changed_fields, invalid_field


class SaveAvailabilityRuleUseCase(SaveAvailabilityRule):
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
        self._clock = clock
        self._directory = directory
        self._rules = rules
        self._writes = ClinicianWrites(
            clock=clock,
            uow=uow,
            audit=audit,
            directory=directory,
            refresh=refresh,
            entity_type="availability_rule",
        )

    def execute(self, *, actor: Id, rule_id: Id | None, fields: Mapping[str, str]) -> Id:
        clinician = self._writes.caller(actor)
        before = (
            self._writes.owned(self._rules.get(rule_id), rule_id, clinician) if rule_id else None
        )
        today = self._clock.now().astimezone(ZoneInfo(clinician.time_zone)).date()
        after = AvailabilityRule.from_form(
            fields,
            id=before.id if before else Id(),
            clinician_id=clinician.id,
            valid_from=before.valid_from if before else today,
            valid_to=before.valid_to if before else None,
        )
        metadata: dict[str, object] = {"weekday": after.weekday}
        if before:
            metadata["changed"] = changed_fields(before, after)
        self._writes.commit(
            actor=actor,
            clinician=clinician,
            action="updated" if before else "created",
            entity_id=after.id,
            metadata=metadata,
            write=lambda: self._save(after, clinician),
        )
        return after.id

    def _save(self, rule: AvailabilityRule, clinician: Clinician) -> None:
        if rule.room_id is not None:
            room = self._directory.room(rule.room_id)
            if room is None or not room.active or room.department_id != clinician.department_id:
                raise invalid_field("room_id", "Choisissez une salle active de votre département.")
        self._rules.lock_clinician(clinician.id)
        for other in self._rules.for_clinician(clinician.id):
            if rule.clashes_with(other):
                raise invalid_field("start", f"Cette plage chevauche la plage {other.label}.")
        self._rules.save(rule)
