<!-- aidd_rule:{"version":1,"category":"00-architecture","slug":"0-ports-and-use-cases","description":"Shape of ports, use cases, adapters and their wiring","paths":["src/drlibre/**/application/**/*.py","src/drlibre/**/infrastructure/**/*.py","src/drlibre/bootstrap/**/*.py"],"targets":["claude"]} -->
# Ports and use cases

## Ports
- Declare inbound ports in `application/ports/inbound.py` and outbound ports in `application/ports/outbound.py`.
- A port is a `typing.Protocol` whose every method has a one-line docstring stating its contract, including failure behaviour.
- Put data a port exchanges beside it as a frozen dataclass.

## Use cases
- Name a use case `<Port>UseCase`, place it in `application/use_cases/<snake_name>.py`, inherit its inbound port explicitly and expose one `execute()` method.
- Inject clock and outbound ports through `__init__` into private `_attributes`; never instantiate an adapter inside a use case.

## Adapters and wiring
- An adapter inherits its outbound port explicitly and is named after its technology, such as `DjangoDatabaseProbe` or `SmtpMailer`.
- Wire adapters to use cases only in `bootstrap/container.py`, with keyword arguments; interfaces reach use cases only through `container()`.
