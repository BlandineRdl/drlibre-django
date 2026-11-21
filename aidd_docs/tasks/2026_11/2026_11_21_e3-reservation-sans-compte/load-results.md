# Load results E3

## Setup
- Machine: Apple M4, 10 cores, 24 GB, macOS 26.6.2, Docker 29.8.2 (compose stack on the same machine, Locust on the host).
- Data: `python -m scripts.seed --size load`, 10 seeded hospitals (8 load + 2 demo), 200 load clinicians, 5 000 patients, 50 000 appointments, about 107 000 free slots; seed rerun adds nothing.
- Run: `NETWORK_HOURLY_LIMIT=100000` in `.env` for the run, then removed and the stack recreated.
- Command: `uv run locust -f loadtests/locustfile.py --headless -u 20 -r 5 -t 2m --host http://localhost:8000`.
- Booking reads the code from Mailpit's API; the signed-in booking reuses the session the verification opened.

## p95 per endpoint (ms)
| Endpoint | Requests | p95 | Failures |
| --- | --- | --- | --- |
| GET `/api/v1/search/providers` | 550 | 140 | 0 |
| GET `/api/v1/search/hospitals` | 280 | 56 | 0 |
| GET `/api/v1/search/specialties` | 245 | 60 | 0 |
| GET `/` (search page) | 174 | 95 | 0 |
| GET `/api/v1/providers/{id}` | 273 | 55 | 0 |
| GET `/api/v1/slots` | 630 | 65 | 0 |
| POST `/api/v1/booking/holds` | 88 | 92 | 0 |
| POST `/api/v1/booking/holds/{id}/verify` | 88 | 180 | 0 |
| POST `/api/v1/appointments` (signed in) | 88 | 170 | 0 |
| Aggregated | 2 436 | 130 | 0 |

## Verdict
- Every p95 is under 200 ms; no index was added, so no `EXPLAIN ANALYZE` was needed.
- Verify and signed-in booking are the closest to the limit (180 and 170 ms): they write the appointment, rebuild the clinician's slots and audit inside one transaction.
- A taken slot (409) counts as a business refusal, not a failure.
