from datetime import datetime

from django.db.models import Q, QuerySet

from drlibre.booking.application.ports.inbound import (
    AppointmentQueries,
    AppointmentStatus,
    BookedPeriod,
)
from drlibre.booking.infrastructure.django.models import AppointmentRecord
from drlibre.booking.infrastructure.repositories import active_appointments
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id


def _dependents(rows: QuerySet[AppointmentRecord]) -> tuple[Dependent, ...]:
    ordered = rows.order_by("start").values_list("id", "start")
    return tuple(
        Dependent("appointment", Id(row_id), f"Rendez-vous du {start:%d/%m/%Y %H:%M} UTC")
        for row_id, start in ordered
    )


class DjangoBookingQueries(AppointmentQueries):
    """Reads the appointment table; labels carry a start time, never a person."""

    def periods_of(
        self, clinician_id: Id, *, start: datetime, end: datetime
    ) -> tuple[BookedPeriod, ...]:
        rows = AppointmentRecord.objects.filter(
            clinician_id=clinician_id.value, start__lt=end, end__gt=start
        ).order_by("start")
        return tuple(
            BookedPeriod(row.start, row.end, AppointmentStatus(row.status)) for row in rows
        )

    def dependents_of_type(self, appointment_type_id: Id) -> tuple[Dependent, ...]:
        return _dependents(
            AppointmentRecord.objects.filter(appointment_type_id=appointment_type_id.value)
        )

    def dependents_of_room(self, room_id: Id) -> tuple[Dependent, ...]:
        return _dependents(AppointmentRecord.objects.filter(room_id=room_id.value))

    def dependents_of_clinician(self, clinician_id: Id) -> tuple[Dependent, ...]:
        return _dependents(AppointmentRecord.objects.filter(clinician_id=clinician_id.value))

    def active_upcoming_for_clinician_user(
        self, user_id: Id, *, after: datetime
    ) -> tuple[Dependent, ...]:
        rows = active_appointments().filter(clinician__user_id=user_id.value, start__gt=after)
        return _dependents(rows)

    def any_for_user(self, user_id: Id) -> tuple[Dependent, ...]:
        rows = AppointmentRecord.objects.filter(
            Q(patient_id=user_id.value) | Q(clinician__user_id=user_id.value)
        )
        return _dependents(rows)
