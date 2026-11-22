# Load results E8
## Setup
- Machine: Apple M4, 10 cores, 24 GB, macOS 26.6.2, Docker (stack and Locust on the same machine); demo stack stopped during the run. Figures are machine-specific.
- Data: `./scripts/load-run.sh` (own compose project `drlibre-load`, fresh volume removed at exit, image built from the working tree at `6a70a9d` plus the new Locust task), `python -m scripts.seed --size load` and `ANALYZE`: 10 hospitals, 200 load clinicians, 5 000 patients, 50 000 appointments.
- Command: `./scripts/load-run.sh --csv <scratch>/load` (Locust `--headless -u 20 -r 5 -t 2m`, `NETWORK_HOURLY_LIMIT=100000`).
- New task « fhir slot search »: `GET /fhir/Slot?service-type=<type>&start=ge<first>&start=lt<first + 7 days>` without a token, for a random provider's next free type.

## p95 of successful requests per endpoint (ms)
| Endpoint | Successes | p50 | p95 | E7 p95 |
| --- | --- | --- | --- | --- |
| GET `/fhir/Slot` (FHIR search) | 172 | 56 | 88 | new |
| GET `/api/v1/search/providers` | 499 | 39 | 63 | 65 |
| GET `/api/v1/search/hospitals` | 234 | 29 | 54 | 54 |
| GET `/api/v1/search/specialties` | 226 | 28 | 55 | 58 |
| GET `/` (search page) | 167 | 100 | 140 | 140 |
| GET `/api/v1/providers/{id}` | 244 | 12 | 38 | 37 |
| GET `/api/v1/slots` | 558 | 27 | 61 | 70 |
| POST `/api/v1/booking/holds` | 68 | 27 | 53 | 65 |
| POST `/api/v1/booking/holds/{id}/verify` | 68 | 60 | 100 | 110 |
| POST `/api/v1/appointments` (signed in) | 68 | 47 | 86 | 85 |

## Failures by code
- None: 2 324 requests, 0 failures.

## Verdict
- FHIR `Slot` search p95 88 ms, under 200 ms; it reads a whole department's free slots over a week, hence above `GET /api/v1/slots` (one clinician).
- Every other p95 stays at its E7 level, under 200 ms.
