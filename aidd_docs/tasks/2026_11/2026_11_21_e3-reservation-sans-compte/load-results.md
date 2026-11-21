# Load results E3
## Setup
- Machine: Apple M4, 10 cores, 24 GB, macOS 26.6.2, Docker 29.8.2 (compose stack on the same machine, Locust 2.47.0 on the host).
- Data: empty database (`docker compose down -v`, `up -d --build`), then `python -m scripts.seed --size load`: 10 hospitals (8 load + 2 demo), 200 load clinicians with one room each, 5 000 patients, 50 000 appointments, no room, clinician or patient overlap (checked in SQL: 0 / 0 / 0).
- Reset: the load seed is skipped when load appointments exist; to reseed, empty the database with `docker compose down -v` and start the stack again.
- Run: `NETWORK_HOURLY_LIMIT=100000` in `.env` for the run, then restored and web and worker recreated.
- Command: `uv run locust -f loadtests/locustfile.py --headless -u 20 -r 5 -t 2m --host http://localhost:8000`.
- A request counts as a success only when it really succeeded: hold 201, verify 200 with an appointment, signed-in booking 201. Anything else is reported apart under `<endpoint> refused`, by error code.

## p95 of successful requests per endpoint (ms)
| Endpoint | Successes | p95 | Failures |
| --- | --- | --- | --- |
| GET `/api/v1/search/providers` | 520 | 99 | 0 |
| GET `/api/v1/search/hospitals` | 289 | 33 | 0 |
| GET `/api/v1/search/specialties` | 269 | 50 | 0 |
| GET `/` (search page) | 168 | 100 | 0 |
| GET `/api/v1/providers/{id}` | 277 | 30 | 0 |
| GET `/api/v1/slots` | 634 | 41 | 0 |
| POST `/api/v1/booking/holds` | 94 | 43 | 0 |
| POST `/api/v1/booking/holds/{id}/verify` | 94 | 160 | 0 |
| POST `/api/v1/appointments` (signed in) | 93 | 120 | 1 |

## Failures by code
- `signed-in booking refused: conflict`: 1 (a slot taken meanwhile by another virtual user), excluded from the p95 above.
- No `no_room_available` and no failed verify: all 94 verifications booked an appointment.

## Verdict
- Every p95 of successful requests is under 200 ms; no `EXPLAIN ANALYZE` was needed.
- Verify (160 ms) and signed-in booking (120 ms) are the closest to the limit: they write the appointment, rebuild the clinician's slots and audit inside one transaction.
- The previous results counted 409 as a success and ignored a failed verify (HTTP 200 with a `failure`); the old load seed double-booked rooms, so they did not prove successful bookings.
- Open point: slots ignore rooms, see `aidd_docs/backlog/open-questions.md`.
