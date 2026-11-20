from collections import defaultdict

from drlibre.scheduling.application.ports.inbound import (
    AvailabilityQueries,
    AvailabilityRule,
    RoomUsage,
    TimeOff,
)
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel, TimeOffModel
from drlibre.scheduling.infrastructure.repositories import as_rule, as_time_off
from drlibre.shared_kernel.dependents import Dependent
from drlibre.shared_kernel.ids import Id

_WEEKLY = ("weekday", "start", "end")


class DjangoAvailabilityQueries(AvailabilityQueries, RoomUsage):
    def rule(self, rule_id: Id) -> AvailabilityRule | None:
        row = AvailabilityRuleModel.objects.filter(id=rule_id.value).first()
        return as_rule(row) if row else None

    def time_off(self, time_off_id: Id) -> TimeOff | None:
        row = TimeOffModel.objects.filter(id=time_off_id.value).first()
        return as_time_off(row) if row else None

    def rules_of(self, clinician_id: Id) -> tuple[AvailabilityRule, ...]:
        rows = AvailabilityRuleModel.objects.filter(clinician_id=clinician_id.value)
        return tuple(as_rule(row) for row in rows.order_by(*_WEEKLY))

    def time_offs_of(self, clinician_id: Id) -> tuple[TimeOff, ...]:
        rows = TimeOffModel.objects.filter(clinician_id=clinician_id.value).order_by("start", "end")
        return tuple(as_time_off(row) for row in rows)

    def weekly_summary(
        self, clinician_ids: frozenset[Id]
    ) -> dict[Id, tuple[AvailabilityRule, ...]]:
        ids = [i.value for i in clinician_ids]
        rows = AvailabilityRuleModel.objects.filter(clinician_id__in=ids).order_by(*_WEEKLY)
        grouped: defaultdict[Id, list[AvailabilityRule]] = defaultdict(list)
        for row in rows:
            grouped[Id(row.clinician_id)].append(as_rule(row))
        return {clinician: tuple(rules) for clinician, rules in grouped.items()}

    def rules_using(self, room_id: Id) -> tuple[Dependent, ...]:
        rows = AvailabilityRuleModel.objects.filter(room_id=room_id.value).order_by(*_WEEKLY)
        return tuple(
            Dependent("availability_rule", rule.id, rule.label) for rule in map(as_rule, rows)
        )
