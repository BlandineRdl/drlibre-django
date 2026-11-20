---
objective: "Staff sign in by password, each role reaches only its area, and the admin manages hospitals, specialties, departments, rooms, appointment types, users and clinician profiles with audited writes and refused deletes that list their dependents."
status: implemented
---

# Plan: E1 - Le personnel se connecte et gère le référentiel multi-hôpitaux
Source: GitHub issue #4, `aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md` and its 11 Stories in `aidd_docs/backlog/stories/` (`parent:` that Epic); spec §3, §4, §10, §12, §14, §16.

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | Audit, unit of work and web shell | [`phase-1.md`](./phase-1.md) | none |
| 2 | Identity: password sign-in, sessions, access, password change | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Organisation referential and its admin screens | [`phase-3.md`](./phase-3.md) | 2 |
| 4 | Users and clinician profiles | [`phase-4.md`](./phase-4.md) | 3 |
| 5 | Demo seed, end-to-end journey, docs | [`phase-5.md`](./phase-5.md) | 4 |

## External sources
| URL | What it settled |
| --- | --- |
| https://pypi.org/pypi/argon2-cffi/json | argon2-cffi 25.1.0 is current; Django's `Argon2PasswordHasher` needs it (INSTALL.md lists it, `pyproject.toml` lacks it) |
| https://registry.npmjs.org/@picocss/pico/latest | Pico.css 2.1.1 is current; vendored like HTMX |
| https://pypi.org/pypi/pytest-playwright/json | pytest-playwright 0.10.0, playwright 1.65.2, Python >=3.10 |
| https://registry.npmjs.org/axe-core/latest | axe-core 4.14.1 is current; vendored under `tests/e2e/vendor/` for the WCAG check |
| https://pypi.org/pypi/redis/json | redis-py 8.1.0; already locked through `celery[redis]` (`uv.lock` line 849), declared directly since the lockout adapter imports it |
| https://docs.djangoproject.com/en/6.1/topics/auth/passwords/ | `make_password` / `check_password` / `PASSWORD_HASHERS` usable without `django.contrib.auth` in `INSTALLED_APPS`; unverified, executor confirms by running the hasher contract test |

## Impact
| Category | Verdict and evidence | Handled in |
| --- | --- | --- |
| runtime | PostgreSQL, Redis, Mailpit through `docker compose up -d`; stack not running now (`docker compose ps` empty), unverified until started; Playwright needs `uv run playwright install chromium` locally, unverified | 1, 2, 5 |
| regression | low: changes `config/settings.py`, `config/urls.py`, `config/middleware.py`, `container.py`, `tests/conftest.py`, `pyproject.toml`, `scripts/seed.py`; baseline observed `uv run pytest -m "not integration"` → 27 passed, 5 deselected (integration not run, stack down); no safety-net phase, phase 1 re-runs the full suite before and after | 1 |
| architecture | starts from one layers contract over `drlibre.health` and `drlibre.notifications` (`pyproject.toml` importlinter section, observed); intends `audit`, `identity`, `organisation` contexts and `interfaces/web`, first models and migrations, cross-context calls through ports, layers contract extended to the new containers plus a forbidden contract between contexts' inner layers | 1, 2, 3, 4 |
| documentation | `aidd_docs/memory/codebase-map.md` (new contexts, web), `aidd_docs/memory/coding-assertions.md` (e2e and Playwright install), `aidd_docs/memory/architecture.md` (session cookie, origin check, null adapters), `README.md` (demo sign-ins), `.env.example` unchanged | 5 |

## Rules
| Rule | Why it applies |
| --- | --- |
| `aidd_docs/rules/00-architecture/0-ports-and-use-cases.md` | every new port, use case and adapter; wiring only in `container.py` |
| `aidd_docs/rules/02-programming-languages/2-python-value-objects.md` | entities and payloads frozen dataclasses, `Id`, `StrEnum` roles, time from `Clock` |
| `aidd_docs/rules/05-testing/5-fakes-and-contracts.md` | one fake and one contract suite per new outbound port |
| `aidd_docs/rules/06-design-patterns/6-domain-errors.md` | `invalid_input`, `unauthenticated`, `forbidden`, `not_found`, `has_dependents` |
| Spec §4: audit in the same transaction, no personal data in metadata | every write use case |
| Spec §4: identity from session, never the body | admin self-protection, password change |
| Gotcha: Ninja checks CSRF only inside cookie auth | `POST /auth/login` is anonymous, needs the origin check |
| Gotcha: store only a hash of session keys | own session model, Django sessions not used |
| WCAG 2.2 AA, 375-1440 px, presenters build ViewModels | every screen |
| One-line comments only | user global rule |

## Decisions
| Decision | Why |
| --- | --- |
| Contexts `audit` (write side only), `identity` (users, sessions, credentials, lockout, access), `organisation` (hospital, specialty, department, room, appointment type, clinician profile) | INSTALL.md bounded contexts; audit consultation is Epic supervision |
| `UnitOfWork` Protocol in `shared_kernel/unit_of_work.py`, `DjangoUnitOfWork` (`transaction.atomic`) in `audit/infrastructure`; every write use case runs write + `AuditLog.record` inside it | §4 one transaction per change; audit failure raises and rolls back |
| Own `Session` model (token SHA-256 hash, user, expires_at, user_agent), cookie `drlibre_session` HttpOnly, SameSite=Lax, Secure when `HTTPS_ONLY`; `django.contrib.sessions` and `django.contrib.auth` stay out of `INSTALLED_APPS` | gotcha "store only a hash"; Lax keeps Epic 3 email links working |
| Password hashing behind a `PasswordHasher` port, adapter uses Django hashers with `Argon2PasswordHasher` first; unknown email runs one verify against a fixed dummy hash | §12.1 slow salted hash, same time for both failures |
| Lockout counter behind a `FailedSignIns` port, Redis sorted set per SHA-256 of the email, 15-min sliding window; checked before the password, cleared on success | Redis is the rate-limit store; no email in Redis keys |
| Lockout and bad credentials both answer `unauthenticated` (401); lockout message says to retry later | spec §4 has no 429; lockout counts any address, so it reveals no account |
| `User.must_change_password` set when the admin creates a user; a web gate sends that user to the change form before any other page of their area | shadow-report decision: forced change after a temporary password |
| Areas: `/console/` admin, `/workspace/` clinician, `/portal/` patient, `/sign-in`, `/sign-out`, `/account/password`; `require_role` view decorator; no session → redirect to `/sign-in?next=`, other role → 403 "forbidden" page | §12.3 |
| `SameOriginMiddleware` refuses unsafe methods whose `Origin` (or `Sec-Fetch-Site: cross-site`) is not this host with `forbidden` (403); Django CSRF stays on for web forms | §12.3 and the Ninja anonymous-POST gotcha |
| Ownership guard `authorize_owned(record, owner_id, identity)` in `identity/application/access.py`: absent → `not_found`, other owner → `forbidden`, admin passes; proven in `access.feature` now, used by Epics 3-6 for owned records; E1's own screens are admin-global; inactive records stay visible to the admin | Story "chaque rôle" bullet 3; §17.2; the admin must reactivate records |
| Writes: one `Save<X>UseCase` (create or update) and one `Delete<X>UseCase` per entity; reads through a `ReferenceQueries` SQL port returning `Page[T]` (20 rows, total, search on name or code) | light CQRS from architecture.md, keeps the use-case count bounded |
| Codes unique per entity type, globally; room equipment entered comma-separated, stored as tuple; colour `#RRGGBB`; time zone validated against `zoneinfo.available_timezones()` | §3.1 "unique code"; hospital time zone drives later Epics |
| Dependents not yet modelled (appointments, availability rules, waitlist entries) are read through `ScheduleDependents` ports with null adapters returning none, wired until Epics 2-5 replace them; BDD scenarios prove the refusals on fakes | rules of §10 and the Epic are testable now without inventing tables |
| A room moved to another department while clinicians of the old one use it as default → `has_dependents` listing those clinicians | it lists what still uses the record |
| Clinician profile: attach and edit; organisation checks "active clinician user with no profile" through a `StaffDirectory` port whose adapter calls identity's inbound query | contexts reach each other only through ports |
| Delete confirmation is a GET confirm page then a POST, no JavaScript; first invalid field gets `autofocus` and errors `aria-describedby` | §16 confirm first, WCAG without inline scripts under the CSP |
| API: `POST /api/v1/auth/login` returns 200 `{role, home}` and sets the cookie; `POST /api/v1/auth/logout` returns 204 | §14; forced password change is enforced by the web gate only, no other API endpoint exists yet for staff |
| E2E: one pytest-playwright journey marked `e2e`, excluded from the default run and CI, with vendored axe-core at 375 and 1440 px | testing.md "a few Playwright e2e"; CI has no browser install today |
| Seed: two hospitals, departments, rooms, types, specialties, one demo account per role with a fixed demo password documented in README | Epic assumption "référentiel + un compte par rôle"; fictitious, localhost only |
| Un praticien qui a un profil ne peut être ni supprimé ni changé de rôle | sinon le profil orphelin bloque à jamais les suppressions de son département, de sa spécialité et de sa salle ; validée par le PO le 2026-11-20 et ajoutée à la Story « L'admin gère les comptes » |
