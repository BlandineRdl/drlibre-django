<!-- aidd_rule:{"version":1,"category":"02-programming-languages","slug":"2-python-value-objects","description":"Immutable value objects and modern typing in Python 3.13","paths":["src/**/*.py"],"targets":["claude"]} -->
# Python value objects
- Model value objects and port payloads as `@dataclass(frozen=True, slots=True)`; use tuples, not lists, for their sequences.
- Model closed sets of values as `StrEnum` and compare members with `is`.
- Use PEP 695 syntax: `class Ok[T]`, `type Result[T, E] = ...`; no `TypeVar` or `typing.List`-style aliases.
- Build derived values through a named `@classmethod` constructor, such as `HealthReport.from_probes`, with keyword-only arguments.
- Identify entities with `shared_kernel.ids.Id`, parsed with `Id.parse`; never pass raw UUID strings across layers.
- Get the current time only from the `Clock` port, time zone aware; never call `datetime.now()` outside `SystemClock`.
- Take "today" in the application time zone injected through the container (`at.astimezone(zone).date()`), never `at.date()` in UTC.
