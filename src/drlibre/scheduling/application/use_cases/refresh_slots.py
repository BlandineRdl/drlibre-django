from zoneinfo import ZoneInfo

from drlibre.scheduling.application.ports.inbound import RefreshSlots
from drlibre.scheduling.application.ports.outbound import (
    AvailabilityRules,
    ClinicianAppointments,
    SchedulingDirectory,
    SlotStore,
    TimeOffs,
)
from drlibre.scheduling.application.use_cases.computed_slots import SlotComputation, slot_horizon
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id


class RefreshSlotsUseCase(RefreshSlots):
    def __init__(
        self,
        *,
        clock: Clock,
        directory: SchedulingDirectory,
        rules: AvailabilityRules,
        time_offs: TimeOffs,
        appointments: ClinicianAppointments,
        store: SlotStore,
    ) -> None:
        self._clock = clock
        self._directory = directory
        self._computation = SlotComputation(
            directory=directory, rules=rules, time_offs=time_offs, appointments=appointments
        )
        self._store = store

    def execute(self, *, clinician_id: Id) -> None:
        clinician = self._directory.clinician(clinician_id)
        if clinician is None:
            self._store.replace(clinician_id, ())
            return
        tz = ZoneInfo(clinician.time_zone)
        kinds = self._directory.appointment_types(clinician.department_id)
        stored = self._computation.slots(
            clinician_id, kinds, slot_horizon(self._clock.now(), tz), time_zone=tz
        )
        self._store.replace(clinician_id, stored)
