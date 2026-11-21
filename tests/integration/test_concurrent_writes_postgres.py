import dataclasses
from collections.abc import Callable
from datetime import UTC, datetime

import pytest

from drlibre.bootstrap.container import real_adapters, wire
from drlibre.scheduling.domain.availability_rule import AvailabilityRule
from drlibre.scheduling.domain.time_off import TimeOff
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel, TimeOffModel
from drlibre.scheduling.infrastructure.repositories import DjangoAvailabilityRules, DjangoTimeOffs
from drlibre.shared_kernel.ids import Id
from tests.builders_scheduling import stored_department, stored_profile
from tests.fakes.clock import FixedClock
from tests.integration.race import Race

pytestmark = [pytest.mark.integration, pytest.mark.django_db(transaction=True)]

NOW = datetime(2026, 11, 20, 10, tzinfo=UTC)


class RacingRules(DjangoAvailabilityRules):
    def __init__(self, race: Race) -> None:
        self._race = race

    def for_clinician(self, clinician_id: Id) -> tuple[AvailabilityRule, ...]:
        # Read before holding, so without the lock both writers miss each other.
        found = super().for_clinician(clinician_id)
        self._race.hold_first()
        return found


class RacingTimeOffs(DjangoTimeOffs):
    def __init__(self, race: Race) -> None:
        self._race = race

    def for_clinician(self, clinician_id: Id) -> tuple[TimeOff, ...]:
        found = super().for_clinician(clinician_id)
        self._race.hold_first()
        return found


def test_two_overlapping_rules_saved_at_once_leave_only_one() -> None:
    """Story plages : une plage chevauchante est refusée, même enregistrée au même instant."""
    race = Race()
    app = wire(
        dataclasses.replace(
            real_adapters(), clock=FixedClock(NOW), availability_rules=RacingRules(race)
        )
    )
    profile = stored_profile(stored_department())

    def save(start: str, end: str) -> Callable[[], object]:
        fields = {"weekday": "1", "start": start, "end": end, "step_minutes": "15"}
        return lambda: app.save_availability_rule.execute(
            actor=profile.user_id, rule_id=None, fields=fields
        )

    outcomes = race.run(save("09:00", "11:00"), save("10:00", "12:00"))

    assert race.second_was_blocked == [True]
    assert outcomes == ["invalid_input", "saved"]
    assert AvailabilityRuleModel.objects.filter(clinician_id=profile.id.value).count() == 1


def test_the_same_time_off_recorded_twice_at_once_is_kept_once() -> None:
    """Story absences : une absence identique est refusée, même déclarée au même instant."""
    race = Race()
    app = wire(
        dataclasses.replace(real_adapters(), clock=FixedClock(NOW), time_offs=RacingTimeOffs(race))
    )
    profile = stored_profile(stored_department())
    fields = {"start": "2026-12-01T09:00", "end": "2026-12-01T12:00", "reason": ""}

    def record() -> object:
        return app.record_time_off.execute(actor=profile.user_id, fields=fields)

    outcomes = race.run(record, record)

    assert race.second_was_blocked == [True]
    assert outcomes == ["invalid_input", "saved"]
    assert TimeOffModel.objects.filter(clinician_id=profile.id.value).count() == 1
