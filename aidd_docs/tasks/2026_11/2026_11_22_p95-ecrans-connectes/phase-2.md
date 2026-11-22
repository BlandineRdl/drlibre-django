---
status: done
---

# Instruction: Locust scenario per signed-in role
## Architecture projection
```txt
.
├── loadtests/
│   └── locustfile.py ✏️
└── scripts/
    └── load-run.sh ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `./scripts/load-run.sh --keep -t 20s` | Load stack up with the load seed | cli |
| Happy path | Locust runs Visitor, Patient, Clinician, Admin | Each endpoint below appears in stats with successes | cli |
| Edge case | A sign-in fails | Counted under `sign-in refused`; the user stops instead of measuring redirects | cli |
| Teardown | `docker compose -p drlibre-load down -v` | Load stack removed | cli |

## Tasks to do
### `1)` Patient
> Measures E4 screens and the patient API list.

1. `Patient(HttpUser)`: `on_start` picks a random `load-patient-NNNNN`, `POST /api/v1/auth/link`, reads the token from the Mailpit email (`token=`), `POST /api/v1/auth/link/verify`.
2. Tasks: `GET /portal/`, `/portal/appointments`, `/portal/notifications`, `GET /api/v1/appointments`.

### `2)` Clinician
> Measures E6 screens and the clinician API list.

1. `Clinician(HttpUser)`: `on_start` signs in a random `load-clinician-NNN` via `POST /api/v1/auth/login` with `LOAD_PASSWORD`; reads appointment ids from `GET /api/v1/appointments` (name `setup`).
2. Tasks: `GET /workspace/`, `/workspace/calendar`, `/workspace/appointments/{id}`, `GET /api/v1/appointments`.

### `3)` Admin
> Measures E7 screens and the admin API list.

1. `Admin(HttpUser)`: `on_start` signs in `admin@drlibre.localhost` with `LOAD_PASSWORD`.
2. Tasks: `GET /console/?range=7`, `/console/?range=30`, `/console/appointments/` filtered (`status`, `from`/`to`, `department`) and paginated (`page`), `/console/appointments/export.csv` filtered, `/console/audit/` (page and `entity_type` filter), `GET /api/v1/appointments` with filters (`from`/`to` as aware datetimes, the console takes dates).

### `4)` Counting and wiring
1. Success = 200 without redirect (`allow_redirects=False`); else `_count` reports a refusal by name.
2. Stable readable request names (`portal home`, `console dashboard 30d`, …).
3. A sign-in refusal (bad status or no Mailpit token) is counted under `sign-in refused`; an admin or clinician password refusal quits the run to avoid lockouts.
4. `load-run.sh` sets `LOAD_PASSWORD` from `scripts.seed.DEMO_PASSWORD` inside the web container after the seed; update the locustfile docstring.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | Stats list portal home, appointments, notifications and patient API list with successes |
| 2 | Stats list workspace today, calendar, appointment file and clinician API list with successes |
| 3 | Stats list dashboard 7 d and 30 d, filtered list, later page, export, audit and admin API list with successes |
| 4 | `uv run ruff check .` and `uv run ruff format --check .` pass; a short run shows 0 `sign-in refused` |
