# Load results #23
## Setup
- Machine: Apple M4, 10 cores, 24 GB, macOS 26.6.2, Docker 29.8.2 (compose project `drlibre-load` on the same machine, Locust 2.47.0 on the host).
- Data: fresh volume, `python -m scripts.seed --size load`: 10 hospitals (8 load + 2 demo), 200 load clinicians signing in with the demo password, 5 000 patients, 50 108 appointments (50 000 load + 108 demo), 50 430 audit entries (50 000 load, one per load appointment, + 430 demo), 25 055 notifications (one per future BOOKED load appointment, plus the demo seed's).
- Users: `-u 20` shared by weight: 8 `Visitor`, 4 `Patient` (sign-in link from Mailpit), 4 `Clinician` (random load clinician), 4 `Admin` (`admin@drlibre.localhost`).
- Command: `./scripts/load-run.sh --keep --only-summary --csv <dir>/run` (`-u 20 -r 5 -t 3m`; the default went from 2 to 3 min because a 30 s probe gave admin endpoints ~0.4 req/s, under 50 successes in 2 min).
- A request counts as a success only on HTTP 200 without redirect (`allow_redirects=False`); anything else is reported apart under `<endpoint> refused`.

## p95 of successful requests per endpoint (ms)
| Role | Endpoint | Successes | p95 | Failures |
| --- | --- | --- | --- | --- |
| Patient | GET `/portal/` | 165 | 110 | 0 |
| Patient | GET `/portal/appointments` | 180 | 160 | 0 |
| Patient | GET `/portal/notifications` | 174 | 86 | 0 |
| Patient | GET `/api/v1/appointments` | 167 | 170 | 0 |
| Clinician | GET `/workspace/` | 145 | 130 | 0 |
| Clinician | GET `/workspace/calendar` | 169 | **200** | 0 |
| Clinician | GET `/workspace/appointments/{id}` | 172 | 190 | 0 |
| Clinician | GET `/api/v1/appointments` | 177 | 130 | 0 |
| Admin | GET `/console/?range=7` | 89 | 180 | 0 |
| Admin | GET `/console/?range=30` | 96 | **240** ([#25](https://github.com/BlandineRdl/drlibre-django/issues/25)) | 0 |
| Admin | GET `/console/appointments/` filtered (status, from/to, department) | 82 | 130 | 0 |
| Admin | GET `/console/appointments/?page=2..50` | 83 | **220** | 0 |
| Admin | GET `/console/appointments/export.csv` filtered | 73 | **210** | 0 |
| Admin | GET `/console/audit/?page=1..50` | 72 | 130 | 0 |
| Admin | GET `/console/audit/?entity_type=appointment` | 89 | 120 | 0 |
| Admin | GET `/api/v1/appointments` filtered | 85 | 77 | 0 |
| Visitor | GET `/api/v1/search/providers` | 351 | 170 | 0 |
| Visitor | GET `/api/v1/search/hospitals` | 140 | 130 | 0 |
| Visitor | GET `/api/v1/search/specialties` | 157 | 160 | 0 |
| Visitor | GET `/` (search page) | 105 | **310** ([#27](https://github.com/BlandineRdl/drlibre-django/issues/27)) | 0 |
| Visitor | GET `/api/v1/providers/{id}` | 166 | 140 | 0 |
| Visitor | GET `/api/v1/slots` | 352 | 160 | 0 |
| Visitor | POST `/api/v1/booking/holds` | 49 | 170 | 0 |
| Visitor | POST `/api/v1/booking/holds/{id}/verify` | 49 | 240 | 0 |
| Visitor | POST `/api/v1/appointments` (signed in) | 49 | 260 | 0 |

## Failures by code
- None: 3 465 requests, 0 failures, 0 `sign-in refused` (16 sign-ins).

## Fixes
- #25 `/console/?range=30`: one statement for tally, days and busiest, each appointment's zone converted once; SQL 3 × ~50 ms → ~39 ms, median 160 → 87 ms, p95 360 → 240 ms.
- #26 `/console/audit/`: `entity_types()` by loose index scan on `audit_entry_target_at`; 21 ms → 0.2 ms, p95 210 → 130 ms.

## Verdict
- Rerun after #25 and #26, host under other workloads (load average ~4.5 at start, 10 cores): endpoints with unchanged code rose too, e.g. export 110 → 210 ms, `/workspace/calendar` 88 → 200 ms; a second run at load average 12 was discarded (aggregate p95 400 ms).
- Every endpoint of #23 has at least 50 successes; 12 of 16 are under 200 ms.
- Still ≥ 200 ms in this run:
  - `/console/?range=30` (240 ms): the SQL is down to ~39 ms and the page to ~50 ms of server work alone (activity 35 ms, schedules 7 ms, available minutes 8 ms); the remaining p95 is queueing under load, a covering index on `start` saved only ~3 ms so it was not added.
  - `/console/appointments/?page=2..50` (220 ms), export (210 ms), `/workspace/calendar` (200 ms): unchanged code, 170, 110 and 88 ms in the previous run; to re-measure on an idle host before opening issues.
  - `/` search page (310 ms, outside #23's list): see #27.
- Booking hold, verify and signed-in booking have 49 successes each: Visitor endpoints, outside #23's list.
