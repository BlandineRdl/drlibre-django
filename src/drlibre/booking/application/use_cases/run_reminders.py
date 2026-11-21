from drlibre.booking.application.ports.inbound import RunReminders, SendReminders
from drlibre.booking.application.ports.outbound import Staff
from drlibre.booking.application.use_cases.admin_only import refuse_non_admin
from drlibre.shared_kernel.ids import Id


class RunRemindersUseCase(RunReminders):
    def __init__(self, *, staff: Staff, send_reminders: SendReminders) -> None:
        self._staff = staff
        self._send_reminders = send_reminders

    def execute(self, *, actor_id: Id) -> int:
        refuse_non_admin(self._staff, actor_id)
        return self._send_reminders.execute()
