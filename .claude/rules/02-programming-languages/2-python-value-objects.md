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

<!-- aidd_rule_output:path=.claude/rules/02-programming-languages/2-python-value-objects.md sha256=876fc6e9764dc2ec9fa73cdfe4692417f6b2922be6a783846946f090e7b61770 -->
