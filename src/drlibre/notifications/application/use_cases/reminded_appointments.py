from drlibre.notifications.application.ports.inbound import RemindedAppointments
from drlibre.notifications.application.ports.outbound import Notifications
from drlibre.shared_kernel.ids import Id


class RemindedAppointmentsUseCase(RemindedAppointments):
    def __init__(self, *, notifications: Notifications) -> None:
        self._notifications = notifications

    def execute(self, *, appointment_ids: frozenset[Id]) -> frozenset[Id]:
        return self._notifications.reminded_among(appointment_ids)
