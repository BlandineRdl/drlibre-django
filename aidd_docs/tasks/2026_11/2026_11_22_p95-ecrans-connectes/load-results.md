# Load results #23
## Setup
- Machine: Apple M4, 10 cores, 24 GB, macOS 26.6.2, Docker 29.8.2 (compose project `drlibre-load` on the same machine, Locust 2.47.0 on the host); other stacks stopped, load average 3.5 at start.
- Data: fresh volume, `python -m scripts.seed --size load`: 10 hospitals (8 load + 2 demo), 200 load clinicians signing in with the demo password, 5 000 patients, 50 108 appointments (50 000 load + 108 demo), 50 430 audit entries (50 000 load, one per load appointment, + 430 demo), 25 055 notifications (one per future BOOKED load appointment, plus the demo seed's).
- Users: `-u 20` shared by weight: 8 `Visitor`, 4 `Patient` (sign-in link from Mailpit), 4 `Clinician` (random load clinician), 4 `Admin` (`admin@drlibre.localhost`).
- Command: `./scripts/load-run.sh --only-summary --csv <dir>/run` (`-u 20 -r 5 -t 3m`; the default went from 2 to 3 min because a 30 s probe gave admin endpoints ~0.4 req/s, under 50 successes in 2 min).
- A request counts as a success only on HTTP 200 without redirect (`allow_redirects=False`); anything else is reported apart under `<endpoint> refused`.

## p95 of successful requests per endpoint (ms)
| Role | Endpoint | Successes | p95 | Failures |
| --- | --- | --- | --- | --- |
| Patient | GET `/portal/` | 173 | 37 | 0 |
| Patient | GET `/portal/appointments` | 184 | 32 | 0 |
| Patient | GET `/portal/notifications` | 172 | 30 | 0 |
| Patient | GET `/api/v1/appointments` | 177 | 33 | 0 |
| Clinician | GET `/workspace/` | 173 | 37 | 0 |
| Clinician | GET `/workspace/calendar` | 175 | 38 | 0 |
| Clinician | GET `/workspace/appointments/{id}` | 174 | 51 | 0 |
| Clinician | GET `/api/v1/appointments` | 163 | 53 | 0 |
| Admin | GET `/console/?range=7` | 77 | 54 | 0 |
| Admin | GET `/console/?range=30` | 84 | 97 | 0 |
| Admin | GET `/console/appointments/` filtered (status, from/to, department) | 95 | 56 | 0 |
| Admin | GET `/console/appointments/?page=2..50` | 79 | 110 | 0 |
| Admin | GET `/console/appointments/export.csv` filtered | 92 | 56 | 0 |
| Admin | GET `/console/audit/?page=1..50` | 85 | 28 | 0 |
| Admin | GET `/console/audit/?entity_type=appointment` | 92 | 45 | 0 |
| Admin | GET `/api/v1/appointments` filtered | 80 | 54 | 0 |
| Visitor | GET `/api/v1/search/providers` | 362 | 46 | 0 |
| Visitor | GET `/api/v1/search/hospitals` | 148 | 47 | 0 |
| Visitor | GET `/api/v1/search/specialties` | 155 | 46 | 0 |
| Visitor | GET `/` (search page) | 108 | 83 | 0 |
| Visitor | GET `/api/v1/providers/{id}` | 175 | 27 | 0 |
| Visitor | GET `/api/v1/slots` | 372 | 58 | 0 |
| Visitor | POST `/api/v1/booking/holds` | 42 | 37 | 0 |
| Visitor | POST `/api/v1/booking/holds/{id}/verify` | 42 | 72 | 0 |
| Visitor | POST `/api/v1/appointments` (signed in) | 42 | 54 | 0 |

## Failures by code
- None: 3 550 requests, 0 failures, 0 `sign-in refused` (16 sign-ins).

## Fixes
- #25 `/console/?range=30`: one statement for tally, days and busiest, each appointment's zone converted once; SQL 3 × ~50 ms → ~39 ms; p95 360 → 97 ms.
- #26 `/console/audit/`: `entity_types()` by loose index scan on `audit_entry_target_at`; 21 ms → 0.2 ms; p95 210 → 28 ms.
- #27 `/?moment=morning`: rank on the first slot, page, then the next 3 slots of the 20 kept rows; the shown list's total is reused by the counts; providers SQL 33 + 25 ms → 25 ms per page; p95 240 → 83 ms.

## Verdict
- Every endpoint of #23 has at least 50 successes and a p95 under 200 ms; the highest is the appointments list page 2..50 at 110 ms.
- The first run (before the fixes) measured 360, 210 and 240 ms on the three endpoints above; a rerun on a busy host (load average 4.5 to 14) inflated unchanged endpoints up to 220 ms and was replaced by this one.
- Booking hold, verify and signed-in booking have 42 successes each: Visitor endpoints, outside #23's list.
