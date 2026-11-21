from drlibre.scheduling.application.ports.inbound import ExtendSlotHorizon, RefreshSlots
from drlibre.scheduling.application.ports.outbound import AvailabilityRules
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class ExtendSlotHorizonUseCase(ExtendSlotHorizon):
    def __init__(self, *, uow: UnitOfWork, rules: AvailabilityRules, refresh: RefreshSlots) -> None:
        self._uow = uow
        self._rules = rules
        self._refresh = refresh

    def execute(self) -> None:
        # Only clinicians with rules can hold slots; each rebuild drops their days before today.
        for clinician_id in self._rules.clinicians():
            with self._uow:
                self._refresh.execute(clinician_id=clinician_id)
