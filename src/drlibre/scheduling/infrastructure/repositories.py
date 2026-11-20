from drlibre.scheduling.application.ports.outbound import AvailabilityRules, TimeOffs
from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel, TimeOffModel
from drlibre.shared_kernel.ids import Id


def as_rule(row: AvailabilityRuleModel) -> AvailabilityRule:
    return AvailabilityRule(
        id=Id(row.id),
        clinician_id=Id(row.clinician_id),
        weekday=row.weekday,
        start=row.start,
        end=row.end,
        step_minutes=row.step_minutes,
        room_id=Id(row.room_id) if row.room_id else None,
        valid_from=row.valid_from,
        valid_to=row.valid_to,
    )


def as_time_off(row: TimeOffModel) -> TimeOff:
    return TimeOff(
        id=Id(row.id),
        clinician_id=Id(row.clinician_id),
        start=row.start,
        end=row.end,
        reason=row.reason,
    )


class DjangoAvailabilityRules(AvailabilityRules):
    def get(self, rule_id: Id) -> AvailabilityRule | None:
        row = AvailabilityRuleModel.objects.filter(id=rule_id.value).first()
        return as_rule(row) if row else None

    def save(self, rule: AvailabilityRule) -> None:
        AvailabilityRuleModel.objects.update_or_create(
            id=rule.id.value,
            defaults={
                "clinician_id": rule.clinician_id.value,
                "weekday": rule.weekday,
                "start": rule.start,
                "end": rule.end,
                "step_minutes": rule.step_minutes,
                "room_id": rule.room_id.value if rule.room_id else None,
                "valid_from": rule.valid_from,
                "valid_to": rule.valid_to,
            },
        )

    def delete(self, rule_id: Id) -> None:
        AvailabilityRuleModel.objects.filter(id=rule_id.value).delete()

    def clinicians(self) -> tuple[Id, ...]:
        ids = AvailabilityRuleModel.objects.values_list("clinician_id", flat=True).distinct()
        return tuple(Id(value) for value in ids.order_by())

    def for_clinician(self, clinician_id: Id) -> tuple[AvailabilityRule, ...]:
        rows = AvailabilityRuleModel.objects.filter(clinician_id=clinician_id.value)
        return tuple(as_rule(row) for row in rows)


class DjangoTimeOffs(TimeOffs):
    def get(self, time_off_id: Id) -> TimeOff | None:
        row = TimeOffModel.objects.filter(id=time_off_id.value).first()
        return as_time_off(row) if row else None

    def save(self, time_off: TimeOff) -> None:
        TimeOffModel.objects.update_or_create(
            id=time_off.id.value,
            defaults={
                "clinician_id": time_off.clinician_id.value,
                "start": time_off.start,
                "end": time_off.end,
                "reason": time_off.reason,
            },
        )

    def delete(self, time_off_id: Id) -> None:
        TimeOffModel.objects.filter(id=time_off_id.value).delete()

    def for_clinician(self, clinician_id: Id) -> tuple[TimeOff, ...]:
        rows = TimeOffModel.objects.filter(clinician_id=clinician_id.value)
        return tuple(as_time_off(row) for row in rows)
