from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.booking.application.ports.outbound import BookingNotices, Waitlist
from drlibre.booking.domain.appointment import Appointment
from drlibre.booking.domain.waitlist import WaitlistEntry, oldest
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id


class WaitlistOffers:
    """The spec 5.8 offer of a freed appointment, run in the caller's unit of work."""

    def __init__(
        self, *, clock: Clock, audit: AuditLog, waitlist: Waitlist, notices: BookingNotices
    ) -> None:
        self._clock = clock
        self._audit = audit
        self._waitlist = waitlist
        self._notices = notices

    def offer_freed(self, appointment: Appointment) -> WaitlistEntry | None:
        """Offer the cancelled appointment to the oldest matching entry of another patient."""
        candidates = self._waitlist.candidates_locked(
            appointment_type_id=appointment.appointment_type_id,
            clinician_id=appointment.clinician_id,
            start=appointment.start,
            end=appointment.end,
            excluding_patient=appointment.patient_id,
        )
        chosen = oldest(candidates)
        return None if chosen is None else self.offer(chosen, appointment, actor=None)

    def offer(
        self, entry: WaitlistEntry, appointment: Appointment, *, actor: Id | None
    ) -> WaitlistEntry:
        """OFFERED, saved, audited and notified; conflict when another entry holds the offer."""
        offered = entry.offered(appointment.id)
        self._waitlist.save(offered)
        self._audit.record(
            AuditEntry.from_event(
                actor=actor,
                action="booking.waitlist_offered",
                entity_type="waitlist_entry",
                entity_id=offered.id,
                at=self._clock.now(),
                metadata={"appointment_id": appointment.id},
            )
        )
        self._notices.waitlist_offered(offered, appointment.start, appointment.clinician_id)
        return offered
