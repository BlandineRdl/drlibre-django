from drlibre.booking.application.ports.inbound import OfferCancelledSlot, WaitlistEntry
from drlibre.booking.application.ports.outbound import Appointments, FreeSlots, Staff, Waitlist
from drlibre.booking.application.use_cases.waitlist_offers import WaitlistOffers
from drlibre.booking.domain.waitlist import WaitlistStatus
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork


class OfferCancelledSlotUseCase(OfferCancelledSlot):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        staff: Staff,
        waitlist: Waitlist,
        appointments: Appointments,
        free_slots: FreeSlots,
        offers: WaitlistOffers,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._staff = staff
        self._waitlist = waitlist
        self._appointments = appointments
        self._free_slots = free_slots
        self._offers = offers

    def execute(self, *, actor_id: Id, entry_id: Id) -> WaitlistEntry:
        if not self._staff.is_admin(actor_id):
            raise DomainError(ErrorCode.FORBIDDEN, "Seul un admin propose un créneau.")
        with self._uow:
            entry = self._waitlist.get_locked(entry_id)
            if entry is None:
                raise DomainError(ErrorCode.NOT_FOUND, "Entrée d'attente introuvable.")
            if entry.status is not WaitlistStatus.WAITING:
                raise DomainError(
                    ErrorCode.INVALID_TRANSITION,
                    "Seule une entrée en attente reçoit une offre.",
                    {"status": entry.status.value},
                )
            for cancelled in self._appointments.cancelled_of_type(
                entry.appointment_type_id,
                after=self._clock.now(),
                earliest=entry.earliest,
                latest=entry.latest,
            ):
                if (
                    entry.clinician_id in (None, cancelled.clinician_id)
                    and self._free_slots.is_free(
                        cancelled.clinician_id,
                        cancelled.appointment_type_id,
                        cancelled.start,
                        ignoring_hold=None,
                    )
                    and not self._waitlist.holds_offer(cancelled.id)
                ):
                    return self._offers.offer(entry, cancelled, actor=actor_id)
            raise DomainError(ErrorCode.NOT_FOUND, "Aucun créneau annulé ne convient.")
