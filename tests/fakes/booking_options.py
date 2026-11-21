from dataclasses import dataclass

from drlibre.booking.application.ports.inbound import (
    BookingOption,
    BookingOptionQueries,
    BookingOptions,
)
from drlibre.shared_kernel.ids import Id


@dataclass(frozen=True, slots=True)
class OptionType:
    """A type as its picklist names it; `active` covers its hospital too."""

    name: str
    hospital_name: str
    department_id: Id
    bookable_online: bool = True
    active: bool = True


@dataclass(frozen=True, slots=True)
class OptionClinician:
    name: str
    department: str
    department_id: Id
    active: bool = True


@dataclass(frozen=True, slots=True)
class OptionRoom:
    label: str
    department_id: Id
    active: bool = True


def _sorted(options: list[BookingOption]) -> tuple[BookingOption, ...]:
    return tuple(sorted(options, key=lambda o: (o.label, o.id.value)))


class InMemoryBookingOptionQueries(BookingOptionQueries):
    """Lists `types`, `clinicians` and `rooms` as labelled options."""

    def __init__(self) -> None:
        self.types: dict[Id, OptionType] = {}
        self.clinicians: dict[Id, OptionClinician] = {}
        self.rooms: dict[Id, OptionRoom] = {}

    def type_options(self, *, online_only: bool) -> tuple[BookingOption, ...]:
        return _sorted(
            [
                BookingOption(i, f"{t.name} · {t.hospital_name}")
                for i, t in self.types.items()
                if t.active and (t.bookable_online or not online_only)
            ]
        )

    def clinician_options(self) -> tuple[BookingOption, ...]:
        return _sorted(
            [
                BookingOption(i, f"{c.name} · {c.department}")
                for i, c in self.clinicians.items()
                if c.active
            ]
        )

    def booking_options(self, appointment_type_id: Id) -> BookingOptions:
        kind = self.types.get(appointment_type_id)
        if kind is None:
            return BookingOptions((), ())
        place = kind.department_id
        clinicians = [
            o for o in self.clinician_options() if self.clinicians[o.id].department_id == place
        ]
        rooms = [
            BookingOption(i, r.label)
            for i, r in self.rooms.items()
            if r.department_id == place and r.active
        ]
        return BookingOptions(tuple(clinicians), _sorted(rooms))
