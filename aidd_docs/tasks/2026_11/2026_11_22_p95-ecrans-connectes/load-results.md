# Load results #23
## Setup
- Machine: Apple M4, 10 cores, 24 GB, macOS 26.6.2, Docker 29.8.2 (compose project `drlibre-load` on the same machine, Locust 2.47.0 on the host).
- Data: fresh volume, `python -m scripts.seed --size load`: 10 hospitals (8 load + 2 demo), 200 load clinicians signing in with the demo password, 5 000 patients, 50 108 appointments, 50 430 audit entries (one per load appointment), 25 055 notifications (one per future BOOKED load appointment).
- Users: `-u 20` shared by weight: 8 `Visitor`, 4 `Patient` (sign-in link from Mailpit), 4 `Clinician` (random load clinician), 4 `Admin` (`admin@drlibre.localhost`).
- Command: `./scripts/load-run.sh --keep -t 3m --only-summary --csv <dir>/run` (`-u 20 -r 5`; `-t` raised from 2 min because a 30 s probe gave admin endpoints ~0.4 req/s, under 50 successes in 2 min).
- A request counts as a success only on HTTP 200 without redirect (`allow_redirects=False`); anything else is reported apart under `<endpoint> refused`.

## p95 of successful requests per endpoint (ms)
| Role | Endpoint | Successes | p95 | Failures |
| --- | --- | --- | --- | --- |
| Patient | GET `/portal/` | 168 | 96 | 0 |
| Patient | GET `/portal/appointments` | 183 | 110 | 0 |
| Patient | GET `/portal/notifications` | 176 | 110 | 0 |
| Patient | GET `/api/v1/appointments` | 161 | 76 | 0 |
| Clinician | GET `/workspace/` | 168 | 81 | 0 |
| Clinician | GET `/workspace/calendar` | 187 | 88 | 0 |
| Clinician | GET `/workspace/appointments/{id}` | 169 | 120 | 0 |
| Clinician | GET `/api/v1/appointments` | 163 | 120 | 0 |
| Admin | GET `/console/?range=7` | 82 | 180 | 0 |
| Admin | GET `/console/?range=30` | 79 | **360** ([#25](https://github.com/BlandineRdl/drlibre-django/issues/25)) | 0 |
| Admin | GET `/console/appointments/` filtered (status, from/to, department) | 92 | 120 | 0 |
| Admin | GET `/console/appointments/?page=2..50` | 86 | 170 | 0 |
| Admin | GET `/console/appointments/export.csv` filtered | 82 | 110 | 0 |
| Admin | GET `/console/audit/?page=1..50` | 79 | **210** ([#26](https://github.com/BlandineRdl/drlibre-django/issues/26)) | 0 |
| Admin | GET `/console/audit/?entity_type=appointment` | 73 | 140 | 0 |
| Admin | GET `/api/v1/appointments` filtered | 74 | 88 | 0 |
| Visitor | GET `/api/v1/search/providers` | 354 | 93 | 0 |
| Visitor | GET `/api/v1/search/hospitals` | 160 | 150 | 0 |
| Visitor | GET `/api/v1/search/specialties` | 163 | 91 | 0 |
| Visitor | GET `/` (search page) | 102 | **240** ([#27](https://github.com/BlandineRdl/drlibre-django/issues/27)) | 0 |
| Visitor | GET `/api/v1/providers/{id}` | 144 | 70 | 0 |
| Visitor | GET `/api/v1/slots` | 358 | 130 | 0 |
| Visitor | POST `/api/v1/booking/holds` | 47 | 85 | 0 |
| Visitor | POST `/api/v1/booking/holds/{id}/verify` | 47 | 160 | 0 |
| Visitor | POST `/api/v1/appointments` (signed in) | 47 | 110 | 0 |

## Failures by code
- None: 3 473 requests, 0 failures, 0 `sign-in refused` (16 sign-ins).

## Verdict
- Every endpoint of #23 has at least 50 successes; 14 of 16 are under 200 ms.
- Over 200 ms, diagnosed with `EXPLAIN ANALYZE` on the kept stack, not fixed here:
  - `/console/?range=30` (360 ms): three statements each rebuild the same 30-day CTE over ~22 000 appointments (~50 ms each), see #25.
  - `/console/audit/` (210 ms): `SELECT DISTINCT entity_type` seq-scans the whole append-only journal on every page (21 ms, growing), see #26.
  - `/` search page (240 ms, outside #23's list): next slots computed for all 202 providers before paging; E3 measured 100 ms with visitors alone, see #27.
- Booking hold, verify and signed-in booking have 47 successes each: Visitor endpoints, outside #23's list.
