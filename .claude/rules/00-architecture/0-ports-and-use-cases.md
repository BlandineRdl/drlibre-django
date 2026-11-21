---
paths:
  - "src/drlibre/**/application/**/*.py"
  - "src/drlibre/**/infrastructure/**/*.py"
  - "src/drlibre/bootstrap/**/*.py"
---
# Ports and use cases

## Ports
- Declare inbound ports in `application/ports/inbound.py` and outbound ports in `application/ports/outbound.py`.
- A port is a `typing.Protocol` whose every method has a one-line docstring stating its contract, including failure behaviour.
- Put data a port exchanges beside it as a frozen dataclass.

## Use cases
- Name a use case `<Port>UseCase`, place it in `application/use_cases/<snake_name>.py`, inherit its inbound port explicitly and expose one `execute()` method.
- A port with several read methods is a `*Queries` port implemented in `infrastructure/`; never a `*UseCase`.
- A use case keeps exactly one `execute()`; split it before adding a second public method.
- Inject clock and outbound ports through `__init__` into private `_attributes`; never instantiate an adapter inside a use case.

## Adapters and wiring
- An adapter inherits its port explicitly; a technology adapter is named after its technology, such as `DjangoDatabaseProbe` or `SmtpMailer`.
- A cross-context adapter is named after the context it reaches, such as `BookingSlotRefresh` or `ScheduleAndBookingDependents`.
- Two classes never share a name, even in different contexts.
- Wire adapters to use cases only in `bootstrap/container.py`, with keyword arguments; interfaces reach use cases only through `container()`.

<!-- aidd_rule_output:path=.claude/rules/00-architecture/0-ports-and-use-cases.md sha256=a3cc8bdbee27999335d3ca365f07e5e7976a5df2e8e54e46ec073be51e7c5788 -->
