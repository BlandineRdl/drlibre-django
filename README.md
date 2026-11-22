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
