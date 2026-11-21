---
paths:
  - "src/**/*.py"
---
# Python value objects
- Model value objects and port payloads as `@dataclass(frozen=True, slots=True)`; use tuples, not lists, for their sequences.
- Model closed sets of values as `StrEnum` and compare members with `is`.
- Use PEP 695 syntax: `class Ok[T]`, `type Result[T, E] = ...`; no `TypeVar` or `typing.List`-style aliases.
- Build derived values through a named `@classmethod` constructor, such as `HealthReport.from_probes`, with keyword-only arguments.
- Identify entities with `shared_kernel.ids.Id`, parsed with `Id.parse`; never pass raw UUID strings across layers.
- Get the current time only from the `Clock` port, time zone aware; never call `datetime.now()` outside `SystemClock`.
- Take "today" in the application time zone injected through the container (`at.astimezone(zone).date()`), never `at.date()` in UTC.

<!-- aidd_rule_output:path=.claude/rules/02-programming-languages/2-python-value-objects.md sha256=9bdc40e665c5bb0af00bccb7ccc8bfff181ce8fcb42579ef816969b7dff34c83 -->
