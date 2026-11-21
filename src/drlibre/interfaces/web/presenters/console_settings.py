from dataclasses import dataclass

from drlibre.shared_kernel.booking_policy import (
    BOOKING_LEAD_TIME,
    CANCELLATION_WINDOW,
    MAX_OPEN_ONLINE,
    REMINDER_WINDOW,
    SLOT_HORIZON_DAYS,
)

SETTINGS_URL = "/console/settings/"
REMINDERS_URL = f"{SETTINGS_URL}reminders"


@dataclass(frozen=True, slots=True)
class Fact:
    label: str
    value: str


@dataclass(frozen=True, slots=True)
class SettingsView:
    facts: tuple[Fact, ...]
    notice: str
    reminders_url: str


def _hours(seconds: float) -> str:
    return f"{int(seconds // 3600)} h"


def reminders_notice(count: str) -> str:
    """« N rappels envoyés », singular for 0 and 1; an unusable count shows nothing."""
    if not count.isdigit():
        return ""
    sent = int(count)
    return f"{sent} rappel envoyé" if sent <= 1 else f"{sent} rappels envoyés"


def settings_view(*, done: str, count: str) -> SettingsView:
    return SettingsView(
        facts=(
            Fact(
                "Délai minimal de réservation",
                f"{int(BOOKING_LEAD_TIME.total_seconds() // 60)} min",
            ),
            Fact(
                "Délai d'annulation ou de déplacement", _hours(CANCELLATION_WINDOW.total_seconds())
            ),
            Fact("Réservations en ligne à venir par patient", str(MAX_OPEN_ONLINE)),
            Fact("Rappel envoyé avant le RDV", _hours(REMINDER_WINDOW.total_seconds())),
            Fact("Horizon des créneaux", f"{SLOT_HORIZON_DAYS} jours"),
        ),
        notice=reminders_notice(count) if done == "reminders" else "",
        reminders_url=REMINDERS_URL,
    )
