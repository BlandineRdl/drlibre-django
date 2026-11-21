from datetime import datetime

from django.db.models import Q, QuerySet

from drlibre.booking.application.ports.outbound import Appointments, Holds, VerificationCodes
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.verification_code import CodePurpose, VerificationCode
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.booking.infrastructure.django.models import (
    AppointmentRecord,
    BookingHoldRecord,
    VerificationCodeRecord,
)
from drlibre.shared_kernel.ids import Id

_INACTIVE = (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW)
_ONLINE = (Source.ONLINE, Source.ROUND_ROBIN)


def active_appointments() -> QuerySet[AppointmentRecord]:
    return AppointmentRecord.objects.exclude(status__in=_INACTIVE)


def overlapping(start: datetime, end: datetime) -> Q:
    return Q(start__lt=end, end__gt=start)


class DjangoAppointments(Appointments):
    def add(self, appointment: Appointment) -> None:
        AppointmentRecord.objects.create(
            id=appointment.id.value,
            patient_id=appointment.patient_id.value,
            clinician_id=appointment.clinician_id.value,
            appointment_type_id=appointment.appointment_type_id.value,
            room_id=appointment.room_id.value if appointment.room_id else None,
            start=appointment.start,
            end=appointment.end,
            status=appointment.status.value,
            source=appointment.source.value,
            reason=appointment.reason,
        )

    def conflicting_resources(
        self, *, clinician_id: Id, patient_id: Id, start: datetime, end: datetime
    ) -> tuple[str, ...]:
        rows = active_appointments().filter(overlapping(start, end))
        resources = (
            ("clinician", rows.filter(clinician_id=clinician_id.value).exists()),
            ("patient", rows.filter(patient_id=patient_id.value).exists()),
        )
        return tuple(name for name, hit in resources if hit)

    def clinician_busy(self, clinician_id: Id, start: datetime, end: datetime) -> bool:
        rows = active_appointments().filter(overlapping(start, end))
        return rows.filter(clinician_id=clinician_id.value).exists()

    def open_online_count(self, patient_id: Id, now: datetime) -> int:
        return (
            active_appointments()
            .filter(patient_id=patient_id.value, source__in=_ONLINE, start__gt=now)
            .count()
        )

    def busy_rooms(self, room_ids: tuple[Id, ...], start: datetime, end: datetime) -> frozenset[Id]:
        rows = active_appointments().filter(
            overlapping(start, end), room_id__in=[r.value for r in room_ids]
        )
        return frozenset(Id(room) for room in rows.values_list("room_id", flat=True) if room)


def _hold(row: BookingHoldRecord) -> BookingHold:
    return BookingHold(
        id=Id(row.id),
        clinician_id=Id(row.clinician_id),
        appointment_type_id=Id(row.appointment_type_id),
        start=row.start,
        end=row.end,
        source=Source(row.source),
        details=VisitorDetails(
            full_name=row.full_name,
            birth_date=row.birth_date,
            email=row.email,
            phone=row.phone,
            reason=row.reason,
        ),
        expires_at=row.expires_at,
    )


class DjangoHolds(Holds):
    def add(self, hold: BookingHold) -> None:
        BookingHoldRecord.objects.create(
            id=hold.id.value,
            clinician_id=hold.clinician_id.value,
            appointment_type_id=hold.appointment_type_id.value,
            start=hold.start,
            end=hold.end,
            source=hold.source.value,
            full_name=hold.details.full_name,
            birth_date=hold.details.birth_date,
            email=hold.details.email,
            phone=hold.details.phone,
            reason=hold.details.reason,
            expires_at=hold.expires_at,
        )

    def get(self, hold_id: Id) -> BookingHold | None:
        row = BookingHoldRecord.objects.filter(id=hold_id.value).first()
        return _hold(row) if row else None

    def open_for_email(self, email: str, at: datetime) -> BookingHold | None:
        rows = BookingHoldRecord.objects.filter(email=email, expires_at__gt=at)
        row = rows.order_by("-expires_at").first()
        return _hold(row) if row else None

    def held(
        self,
        clinician_id: Id,
        start: datetime,
        end: datetime,
        *,
        at: datetime,
        excluding: Id | None,
    ) -> bool:
        rows = BookingHoldRecord.objects.filter(
            overlapping(start, end), clinician_id=clinician_id.value, expires_at__gt=at
        )
        if excluding is not None:
            rows = rows.exclude(id=excluding.value)
        return rows.exists()

    def open_in(
        self, clinician_ids: tuple[Id, ...], start: datetime, end: datetime, *, at: datetime
    ) -> tuple[BookingHold, ...]:
        rows = BookingHoldRecord.objects.filter(
            overlapping(start, end),
            clinician_id__in=[c.value for c in clinician_ids],
            expires_at__gt=at,
        )
        return tuple(_hold(row) for row in rows.order_by("start"))

    def expired(self, at: datetime) -> tuple[BookingHold, ...]:
        rows = BookingHoldRecord.objects.filter(expires_at__lte=at)
        return tuple(_hold(row) for row in rows.order_by("expires_at"))

    def delete(self, hold_id: Id) -> None:
        BookingHoldRecord.objects.filter(id=hold_id.value).delete()


class DjangoVerificationCodes(VerificationCodes):
    def put(self, code: VerificationCode) -> None:
        VerificationCodeRecord.objects.update_or_create(
            hold_id=code.hold_id.value,
            defaults={
                "email": code.email,
                "purpose": code.purpose.value,
                "code_hash": code.code_hash,
                "expires_at": code.expires_at,
                "attempts": code.attempts,
            },
        )

    def for_hold(self, hold_id: Id) -> VerificationCode | None:
        row = VerificationCodeRecord.objects.filter(hold_id=hold_id.value).first()
        if row is None:
            return None
        return VerificationCode(
            hold_id=Id(row.hold_id),
            email=row.email,
            purpose=CodePurpose(row.purpose),
            code_hash=row.code_hash,
            expires_at=row.expires_at,
            attempts=row.attempts,
        )

    def delete_for_hold(self, hold_id: Id) -> None:
        VerificationCodeRecord.objects.filter(hold_id=hold_id.value).delete()
