---
objective: "One `docker compose up` starts the 6 services, and `GET /api/v1/health` crosses inbound adapter, use case, outbound port and adapter, with one green test per level and the boundary contracts enforced."
status: pending
---

# Plan: Walking skeleton DrLibre-django
Source: user brief "Task : walking skeleton DrLibre-django" (items 1-11, exclusions, acceptance criteria), prerequisite of `aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md`.

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | Project and tooling | [`phase-1.md`](./phase-1.md) | none |
| 2 | Health slice through the hexagon | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Cross-cutting HTTP concerns | [`phase-3.md`](./phase-3.md) | 2 |
| 4 | Compose stack, Celery, seed, Mailpit | [`phase-4.md`](./phase-4.md) | 3 |
| 5 | Gates: pre-commit and boundary proof | [`phase-5.md`](./phase-5.md) | 4 |

## External sources
| URL | What it settled |
| --- | --- |
| https://pypi.org/pypi/django/json | Django 6.1.3 is current |
| https://pypi.org/pypi/django-ninja/json | Django Ninja 1.8.0 is current |
| https://pypi.org/pypi/celery/json | Celery 5.7.0 is latest; 5.6.3 is the last 5.6, pin `celery>=5.6,<5.7` |
| https://pypi.org/pypi/python-doctor/json | Python Doctor exists on PyPI (saikatkumardey/python-doctor); its pre-commit hook form is unverified, executor checks its README |
| https://docs.djangoproject.com/en/6.1/ref/csp/ | Built-in CSP middleware and `SECURE_CSP` setting; unverified here, executor confirms names |

## Impact
| Category | Verdict and evidence | Handled in |
| --- | --- | --- |
| runtime | Docker and uv present (`docker info` ok, `/Users/blacksun/.local/bin/uv`); ports 8000, 8025, 5432, 6379 must be free, unverified | 4 |
| regression | none: repository holds only docs (`git ls-files`) | none |
| architecture | creates the hexagon layout of `aidd_docs/INSTALL.md` from nothing; import-linter enforces it | 1, 2, 5 |
| documentation | `aidd_docs/memory/codebase-map.md` gains the real top-level areas; `aidd_docs/memory/coding-assertions.md` gains the gate commands; README run steps | 5 |

## Rules
| Rule | Why it applies |
| --- | --- |
| Domain imports only shared kernel and stdlib | contract to prove in phase 5 |
| Interfaces call inbound ports only, wired by `bootstrap/` | the health router must not import infrastructure |
| Ports are `typing.Protocol`, adapters inherit explicitly | `DatabaseProbe`, `Clock`, `Mailer` |
| No mocks on owned ports, in-memory fakes, contract tests keep fakes honest | item 11 |
| Time comes from the `Clock` port | health reports `checked_at` from it |
| Config from `.env` via pydantic-settings, mirrored in `.env.example` | item 2 |
| Logs JSON, carry correlation id, no sensitive data | item 6, spec 16 |
| One-line comments only | user global rule |

## Decisions
| Decision | Why |
| --- | --- |
| `config/` at repo root, not under `src/drlibre/` | `aidd_docs/INSTALL.md` folder structure puts settings, urls, celery and middleware there |
| Health lives in a `health` context with a `DatabaseProbe` port; `Clock` lives in the shared kernel | gives a real outbound port with a fake and a PostgreSQL adapter, so the contract and integration tests test something real |
| `Mailer` port lives in the `notifications` context, with in-memory and SMTP adapters, no business rule | item 11 needs a Mailpit send test; the Epic reuses the port |
| Beat uses a static `beat_schedule` in `config/celery.py`, no django-celery-beat | no model allowed in this slice; one less dependency |
| Dummy task `heartbeat` calls the health use case and logs its result | proves worker and beat run the same use cases as web |
| HTMX 2.0.x vendored as a static file, no template yet | pinned per brief without adding a screen |
| Seed: `scripts/seed.py` running an empty, ordered list of seeders | extension point; idempotent by construction |
| Tests needing PostgreSQL or Mailpit carry a pytest marker and run against the compose services | integration and contract-real tests need real backends |
