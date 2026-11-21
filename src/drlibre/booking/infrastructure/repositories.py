from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet

from drlibre.booking.application.ports.outbound import (
    Appointments,
    ExpiringEntry,
    Holds,
    VerificationCodes,
    Waitlist,
)
from drlibre.booking.domain.appointment import Appointment, AppointmentStatus, Source
from drlibre.booking.domain.hold import BookingHold
from drlibre.booking.domain.verification_code import CodePurpose, VerificationCode
from drlibre.booking.domain.visitor_details import VisitorDetails
from drlibre.booking.domain.waitlist import WaitlistEntry, WaitlistStatus
from drlibre.booking.infrastructure.django.models import (
    AppointmentRecord,
    BookingHoldRecord,
    VerificationCodeRecord,
    WaitlistEntryRecord,
)
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id

_INACTIVE = (AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW)
_ONLINE = (Source.ONLINE, Source.ROUND_ROBIN)


def active_appointments() -> QuerySet[AppointmentRecord]:
    return AppointmentRecord.objects.exclude(status__in=_INACTIVE)


def overlapping(start: datetime, end: datetime) -> Q:
    return Q(start__lt=end, end__gt=start)


_OVERLAP_RESOURCES = {
    "appointment_clinician_no_overlap": "clinician",
    "appointment_patient_no_overlap": "patient",
}


@contextmanager
def _overlap_is_conflict() -> Generator[None]:
    """Turn an exclusion constraint hit, slipped past the locks, into a booking conflict."""
    try:
        with transaction.atomic():
            yield
    except IntegrityError as error:
        name = getattr(getattr(error.__cause__, "diag", None), "constraint_name", None)
        if name not in _OVERLAP_RESOURCES:
            raise
        raise DomainError(
            ErrorCode.CONFLICT,
            "Un rendez-vous actif occupe déjà ce créneau.",
            {"resources": [_OVERLAP_RESOURCES[name]]},
        ) from error


def _fields(appointment: Appointment) -> dict[str, Any]:
    return {
        "patient_id": appointment.patient_id.value,
        "clinician_id": appointment.clinician_id.value,
        "appointment_type_id": appointment.appointment_type_id.value,
        "room_id": appointment.room_id.value if appointment.room_id else None,
        "start": appointment.start,
        "end": appointment.end,
        "status": appointment.status.value,
        "source": appointment.source.value,
        "reason": appointment.reason,
        "cancelled_at": appointment.cancelled_at,
        "cancellation_reason": appointment.cancellation_reason,
        "clinical_notes": appointment.clinical_notes,
    }


def _excluding(
    rows: QuerySet[AppointmentRecord], excluding: Id | None
) -> QuerySet[AppointmentRecord]:
    return rows if excluding is None else rows.exclude(id=excluding.value)


def _appointment(row: AppointmentRecord) -> Appointment:
    return Appointment(
        id=Id(row.id),
        patient_id=Id(row.patient_id),
        clinician_id=Id(row.clinician_id),
        appointment_type_id=Id(row.appointment_type_id),
        room_id=Id(row.room_id) if row.room_id else None,
        start=row.start,
        end=row.end,
        status=AppointmentStatus(row.status),
        source=Source(row.source),
        reason=row.reason,
        cancelled_at=row.cancelled_at,
        cancellation_reason=row.cancellation_reason,
        clinical_notes=row.clinical_notes,
    )


class DjangoAppointments(Appointments):
    def add(self, appointment: Appointment) -> None:
        with _overlap_is_conflict():
            AppointmentRecord.objects.create(id=appointment.id.value, **_fields(appointment))

    def save(self, appointment: Appointment) -> None:
        with _overlap_is_conflict():
            updated = AppointmentRecord.objects.filter(id=appointment.id.value).update(
                **_fields(appointment)
            )
        if not updated:
            raise DomainError(ErrorCode.NOT_FOUND, "Rendez-vous introuvable.")

    def get(self, appointment_id: Id) -> Appointment | None:
        row = AppointmentRecord.objects.filter(id=appointment_id.value).first()
        return _appointment(row) if row else None

    def booked_starting(self, after: datetime, until: datetime) -> tuple[Appointment, ...]:
        rows = AppointmentRecord.objects.filter(
            status=AppointmentStatus.BOOKED.value, start__gt=after, start__lte=until
        )
        return tuple(_appointment(row) for row in rows.order_by("start", "id"))

    def cancelled_of_type(
        self, appointment_type_id: Id, *, after: datetime, earliest: datetime, latest: datetime
    ) -> tuple[Appointment, ...]:
        rows = AppointmentRecord.objects.filter(
            status=AppointmentStatus.CANCELLED.value,
            appointment_type_id=appointment_type_id.value,
            start__gt=after,
            start__gte=earliest,
            end__lte=latest,
        )
        return tuple(_appointment(row) for row in rows.order_by("start", "id"))

    def conflicting_resources(
        self,
        *,
        clinician_id: Id,
        patient_id: Id,
        start: datetime,
        end: datetime,
        excluding: Id | None = None,
    ) -> tuple[str, ...]:
        rows = _excluding(active_appointments().filter(overlapping(start, end)), excluding)
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

    def busy_rooms(
        self,
        room_ids: tuple[Id, ...],
        start: datetime,
        end: datetime,
        excluding: Id | None = None,
    ) -> frozenset[Id]:
        rows = active_appointments().filter(
            overlapping(start, end), room_id__in=[r.value for r in room_ids]
        )
        rows = _excluding(rows, excluding)
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
        return _code(VerificationCodeRecord.objects.filter(hold_id=hold_id.value).first())

    def for_hold_locked(self, hold_id: Id) -> VerificationCode | None:
        rows = VerificationCodeRecord.objects.select_for_update().filter(hold_id=hold_id.value)
        return _code(rows.first())

    def delete_for_hold(self, hold_id: Id) -> None:
        VerificationCodeRecord.objects.filter(hold_id=hold_id.value).delete()


def _code(row: VerificationCodeRecord | None) -> VerificationCode | None:
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


def _entry(row: WaitlistEntryRecord) -> WaitlistEntry:
    return WaitlistEntry(
        id=Id(row.id),
        patient_id=Id(row.patient_id),
        appointment_type_id=Id(row.appointment_type_id),
        clinician_id=Id(row.clinician_id) if row.clinician_id else None,
        earliest=row.earliest,
        latest=row.latest,
        status=WaitlistStatus(row.status),
        created_at=row.created_at,
        offered_appointment_id=(
            Id(row.offered_appointment_id) if row.offered_appointment_id else None
        ),
    )


def _entry_fields(entry: WaitlistEntry) -> dict[str, Any]:
    offered = entry.offered_appointment_id
    return {
        "patient_id": entry.patient_id.value,
        "appointment_type_id": entry.appointment_type_id.value,
        "clinician_id": entry.clinician_id.value if entry.clinician_id else None,
        "earliest": entry.earliest,
        "latest": entry.latest,
        "status": entry.status.value,
        "created_at": entry.created_at,
        "offered_appointment_id": offered.value if offered else None,
    }


@contextmanager
def _taken_offer_is_conflict() -> Generator[None]:
    """Turn a second open offer of one appointment into a conflict."""
    try:
        with transaction.atomic():
            yield
    except IntegrityError as error:
        name = getattr(getattr(error.__cause__, "diag", None), "constraint_name", None)
        if name != "waitlist_one_offer_per_appointment":
            raise
        raise DomainError(
            ErrorCode.CONFLICT,
            "Ce créneau est déjà proposé à une autre entrée.",
            {"resources": ["waitlist_entry"]},
        ) from error


class DjangoWaitlist(Waitlist):
    def add(self, entry: WaitlistEntry) -> None:
        with _taken_offer_is_conflict():
            WaitlistEntryRecord.objects.create(id=entry.id.value, **_entry_fields(entry))

    def save(self, entry: WaitlistEntry) -> None:
        with _taken_offer_is_conflict():
            updated = WaitlistEntryRecord.objects.filter(id=entry.id.value).update(
                **_entry_fields(entry)
            )
        if not updated:
            raise DomainError(ErrorCode.NOT_FOUND, "Entrée d'attente introuvable.")

    def get(self, entry_id: Id) -> WaitlistEntry | None:
        row = WaitlistEntryRecord.objects.filter(id=entry_id.value).first()
        return _entry(row) if row else None

    def get_locked(self, entry_id: Id) -> WaitlistEntry | None:
        row = WaitlistEntryRecord.objects.select_for_update().filter(id=entry_id.value).first()
        return _entry(row) if row else None

    def candidates_locked(
        self,
        *,
        appointment_type_id: Id,
        clinician_id: Id,
        start: datetime,
        end: datetime,
        excluding_patient: Id,
    ) -> tuple[WaitlistEntry, ...]:
        rows = (
            WaitlistEntryRecord.objects.select_for_update()
            .filter(
                Q(clinician_id__isnull=True) | Q(clinician_id=clinician_id.value),
                status=WaitlistStatus.WAITING.value,
                appointment_type_id=appointment_type_id.value,
                earliest__lte=start,
                latest__gte=end,
            )
            .exclude(patient_id=excluding_patient.value)
            .order_by("id")
        )
        return tuple(_entry(row) for row in rows)

    def holds_offer(self, appointment_id: Id) -> bool:
        return WaitlistEntryRecord.objects.filter(
            status=WaitlistStatus.OFFERED.value, offered_appointment_id=appointment_id.value
        ).exists()

    def expiring_locked(self, now: datetime) -> tuple[ExpiringEntry, ...]:
        rows = (
            WaitlistEntryRecord.objects.select_for_update(of=("self",))
            .select_related("offered_appointment")
            .filter(
                Q(status=WaitlistStatus.WAITING.value, latest__lte=now)
                | Q(status=WaitlistStatus.OFFERED.value, offered_appointment__start__lte=now)
            )
            .order_by("id")
        )
        return tuple(
            ExpiringEntry(
                _entry(row), row.offered_appointment.start if row.offered_appointment else None
            )
            for row in rows
        )
