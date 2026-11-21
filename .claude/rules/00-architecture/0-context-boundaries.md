---
paths:
  - "src/drlibre/**/domain/**/*.py"
  - "src/drlibre/**/application/**/*.py"
  - "src/drlibre/**/infrastructure/**/*.py"
  - "pyproject.toml"
---
# Context boundaries
## Imports
- A context's domain and application import only its own ports, the shared kernel and `audit.application.ports`.
- Never import another context's modules from a core, whatever the layer.
- Reach another context through an adapter in your own `infrastructure/` that calls the other context's inbound port.
- Declare the port the adapter implements in your own `application/ports/`.

## Enforcement
- Give every new context an entry in the `layers` contract's `containers` in `pyproject.toml`.
- Give every new context a `forbidden` contract on its domain and application listing each other context.

## Accepted exception
- A lock adapter may lock another context's rows through its ORM model, as in `booking/infrastructure/schedule_locks.py`.
- Never read or write another context's data that way outside a lock adapter.

<!-- aidd_rule_output:path=.claude/rules/00-architecture/0-context-boundaries.md sha256=c1cc94c6560dcd7a7c2469a4760104033a4133a97951e6d4321e71c70ce59120 -->
