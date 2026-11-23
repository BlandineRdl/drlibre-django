# DrLibre-django
Hospital appointment scheduling, a hexagonal Django back end. Portfolio sandbox, fictitious data, localhost only.

## Run
1. `cp .env.example .env` and set a real `SECRET_KEY`.
2. `docker compose up -d --wait` starts web, worker, beat, PostgreSQL, Redis and Mailpit; the web container migrates and seeds the demo data.
3. Optional, for a live demo: `docker compose exec web python -m scripts.seed_showcase` adds two hospitals, 13 clinicians, 600 patients and ~5,600 appointments over the past 6 and next 3 weeks; once per database (`docker compose down -v` to start over). The e2e journeys expect the plain demo seed.
4. `curl -i localhost:8000/api/v1/health` answers 200.

## Try the app
- App: http://localhost:8000, best in a French-locale browser (date fields).
- Mailpit: http://localhost:8025 receives every email: booking codes, sign-in links, confirmations, reminders. Nothing leaves the machine.
- Every account is fictitious; the password is `drlibre-demo-2026`.

### Accounts
| Role | Email | Where to start |
| --- | --- | --- |
| Admin | `admin@drlibre.localhost` | `/console/`: dashboard, appointments, book for a patient, waitlist, audit log, settings |
| Clinician | `clinicien@drlibre.localhost` (Claire Martin, Cardiologie, Hôpital Nord, Lille) | `/workspace/`: today's agenda, calendar, appointment file and notes, availability, time off |
| Clinician | `clinicien2@drlibre.localhost` (Hugo Bernard, same department) | `/workspace/` |
| Patient | `patient@drlibre.localhost` (Paul Patient) | `/portal/`: appointments, cancel, reschedule, `.ics`, notifications, waitlist |
| Passwordless patient | `visiteur@drlibre.localhost` | no password: request a sign-in link at `/sign-in`, open it from Mailpit |

Both demo clinicians work Monday to Friday, 09:00–12:00 and 14:00–17:00 (Paris), editable at `/workspace/availability/`.

Showcase clinicians (step 3), same password, emails ending in `@drlibre.localhost`:

| Hospital | Clinicians |
| --- | --- |
| Hôpital Nord, Lille | `sophie.lefebvre` (Pédiatrie), `thomas.dubois`, `yasmine.benali` (Dermatologie), `camille.moreau` (Neurologie) |
| Hôpital Sud Confluence, Lyon | `ines.garnier`, `julien.laurent` (Orthopédie), `lea.fontaine` (Cardiologie), `nicolas.roux` (Ophtalmologie) |
| Centre hospitalier de l'Estuaire, Nantes | `emilie.mercier` (Gynécologie), `karim.haddad` (Pédiatrie), `lucas.girard`, `marion.chevalier` (Médecine générale) |
| Hôpital Atlantique, Les Abymes | `mathilde.joseph` (Cardiologie) |

The 600 showcase patients (`prenom.nom@patients.drlibre.localhost`) have no password: they sign in by email link.

### Journeys
1. Book without an account: search on `/` (case and accents ignored, e.g. `pediatrie`), pick a slot, enter any name and email, then type the 6-digit code from Mailpit within 10 minutes. The booking opens a 24-hour session on the patient portal.
2. Sort by distance: click « Trier par distance » and allow the browser's location; each result then shows its distance.
3. As a patient, cancel or reschedule more than 24 hours ahead, download the `.ics`, join a waitlist at `/portal/waitlist`.
4. As a clinician, check in, complete or mark a no-show from today's agenda, and write notes in the appointment file.
5. As the admin, book for a patient, offer a freed slot from the waitlist, export appointments as CSV, read the audit log of every write.

Signed in, `GET /api/v1/slots?type=…&clinician=…&start=…&end=…` lists free slots.

### FHIR R4
Under `/fhir`, fictitious and localhost only. Fixed bearer tokens: `demo-admin-token`, `demo-clinician-token`, `demo-patient-token`; issue others with `docker compose exec web python manage.py api_token <email> [--days N] [--revoke]`.
- `curl -i localhost:8000/fhir/metadata` lists every resource, interaction and search parameter.
- `curl 'localhost:8000/fhir/HealthcareService'` then `curl 'localhost:8000/fhir/Slot?service-type=<id>&start=ge2026-12-01T00:00:00%2B01:00&start=lt2026-12-08T00:00:00%2B01:00'` find free slots without a token.
- `curl -H 'Authorization: Bearer demo-patient-token' localhost:8000/fhir/Appointment` lists the demo patient's appointments.

## Technical choices
Django is used as the infrastructure framework (ORM, migrations, HTTP, templates, security middleware), not as the place for business rules. Each departure from the usual Django way is deliberate:

| Choice | Instead of | Why |
| --- | --- | --- |
| Hexagonal architecture per bounded context (`domain`, `application`, `infrastructure`), checked by import-linter | Fat models, logic in views | The domain stays pure Python, tested on in-memory fakes without Django; web, API, FHIR and Celery run the same use cases through one composition root (`bootstrap/container.py`) |
| ORM models live in `<context>/infrastructure/django/` | Models as the domain | Models are persistence adapters behind `typing.Protocol` ports |
| Own session cookie and auth: hashed session tokens, email code, sign-in link, hashed bearer tokens | `django.contrib.auth`, `django.contrib.sessions` | Django stores session keys raw; here only a hash is stored. Django's password hashers are kept |
| Hand-written admin console (`/console/`) | `django.contrib.admin` | Every write goes through a use case, so it is audited and follows the same rules as the other screens |
| Django Ninja for `/api/v1` and `/fhir` | Django REST Framework | Pydantic-native schemas, the same validation as the rest of the code |
| Raw SQL query ports for search, slots, reporting and FHIR reads (light CQRS) | ORM for every read | p95 under 200 ms on the load seed, proven with Locust (`./scripts/load-run.sh`) |
| PostgreSQL guards: `btree_gist` exclusions, partial unique indexes, `select_for_update`, advisory locks, append-only audit triggers | Checks in Python only | No double booking under concurrency, even if a lock is missed |
| Celery with beat | Django's built-in tasks | Django's tasks have no production worker or scheduler yet |
| Hand-written FHIR R4 Pydantic schemas | `fhir.resources` | The library dropped R4 |
| Templates with HTMX and Pico.css; presenters build ViewModels | SPA, logic in templates | Minimal front, no build step, WCAG 2.2 AA |
| Pydantic, pydantic-settings, structlog | `settings.py` constants, stdlib logging | Typed validation at every boundary, typed config from `.env`, JSON logs with a correlation id |
| Gherkin scenarios (pytest-bdd) on fakes, contract tests fake vs real adapter | Mocks, Django `TestCase` | Tests describe behaviour and survive refactoring |

The hexagon pays off where the rules are: `booking` and `scheduling` (placement, locks, round robin, waitlist). `organisation` is mostly reference data CRUD and alone would not justify ports and mapping; it follows the same layout for consistency across the showcase. Read sides (`search`, `reporting`, `interop`) skip the domain and read SQL directly. In practice the ports' value here is in-memory fakes for tests, not swapping providers: no adapter has been replaced. Pattern reference: [Hexagonal Architecture with Django](https://medium.com/@andremrufino/hexagonal-architecture-with-django-fundamentals-and-comparison-with-clean-architecture-38d74608d961) (André Rufino), where Django is the HTTP and persistence adapter.

### How Django-idiomatic is it?
A subjective self-assessment, 0 to 10 per area:

| Area | Score | Why |
| --- | --- | --- |
| ORM, migrations, PostgreSQL constraints | 9 | Idiomatic and advanced (`ExclusionConstraint`, partial indexes, `select_for_update`); only the read sides use raw SQL |
| Security middleware (CSRF, CSP, clickjacking, `check --deploy`) | 9 | Django's own, kept as is |
| Templates, static files | 8 | Django templates and `staticfiles`; logic stays in presenters |
| Config | 6 | `settings.py` fed by pydantic-settings instead of plain constants |
| API | 6 | Django Ninja is well established, DRF remains the canonical choice |
| Forms | 8 | `django.forms` collect, check and render every web form (Django's field templates, one override for Pico); use cases validate again for API and FHIR |
| Auth, sessions | 2 | Own implementation; only Django's password hashers are reused |
| Code organisation | 3 | Hexagonal contexts instead of Django apps with rich models |
| Tests | 3 | pytest-bdd on fakes; no Django `TestCase` for business behaviour |
| Admin | 0 | Not installed, see below |

About 55% overall: Django is used well where it is used (about 85%), but several built-ins are replaced (about 50% coverage).

`django.contrib.admin` is left out on purpose. It writes through the ORM, so it would bypass the use cases: no audit entry in the transaction, no slot refresh, no locks, no dependents check. The console is a business feature of the admin role, not a table editor. A read-only admin for debugging would still require `contrib.auth`, `contrib.sessions` and `contrib.messages`, a second sign-in and raw session keys; `psql`, the console and `/fhir` already cover inspection.

Full rationale and pinned versions: `aidd_docs/INSTALL.md` and `aidd_docs/memory/architecture.md`.

## Develop
1. `uv sync` and `uv run pre-commit install`.
2. With the stack up: `uv run pytest`.
3. `uv run pre-commit run --all-files` runs every gate.
4. End-to-end: `uv run playwright install chromium` once, `docker compose up -d --build`, then `uv run pytest -m e2e`.
   - The journeys write into the stack's database (test hospitals, patients, notifications): keep the demo stack clean by running them on a separate compose project, here on ports 28000:
     ```bash
     export COMPOSE_PROJECT_NAME=drlibre-e2e WEB_PORT=28000 POSTGRES_PORT=25432 REDIS_PORT=26379 MAILPIT_SMTP_PORT=21025 MAILPIT_PORT=28025 NETWORK_HOURLY_LIMIT=100000
     docker compose up -d --build --wait
     E2E_BASE_URL=http://localhost:28000 E2E_MAILPIT_URL=http://localhost:28025 E2E_REDIS_URL=redis://localhost:26379/0 uv run pytest -m e2e
     docker compose down -v
     ```

Design and stack: `aidd_docs/INSTALL.md`.
