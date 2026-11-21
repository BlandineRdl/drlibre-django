# Load results E7
## Setup
- Machine: Apple M4, 10 cores, 24 GB, macOS 26.6.2, Docker (stack and Locust on the same machine); demo stack stopped during runs, other Docker projects idle (< 2 % CPU each).
- Data: `./scripts/load-run.sh` (own compose project `drlibre-load`, fresh volume, image built from the working tree), then `python -m scripts.seed --size load` and `ANALYZE`: 10 hospitals, 200 load clinicians with one room each, 5 000 patients, 50 000 appointments.
- Command: `./scripts/load-run.sh` (Locust `--headless -u 20 -r 5 -t 2m`, `NETWORK_HOURLY_LIMIT=100000`).
- A request counts as a success only when it really succeeded: hold 201, verify 200 with an appointment, signed-in booking 201; refusals are reported apart by error code.

## Cause of the regression
- Room-aware slots (§6.2): `_ROOM_FREE` probed `appointment_room_start` with `start < s."end"` only, so each probe walked the room's past appointments (`Rows Removed by Filter: 136`, 14 073 of 16 538 buffers of the search page query, 48 ms against 4 ms without the filter).
- `FindFreeSlots._with_free_room` compared every slot with every busy room period: 56 056 `Slot.period` calls for one `GET /slots`.
- Bookings: `SlotEngine.free_slots` compared every candidate with every blocked period (83 534 calls per refresh) and `DjangoSlotStore.replace` rewrote ~530 rows per booking, now 7 columns with `TrackedRecord` (22 ms).

## Fix
- GiST index `appointment_room_period` on `(room_id, tstzrange(start, end))` for active appointments (`booking.0007`); `_ROOM_FREE` tests the overlap with `&&`: 48 ms to 28 ms (page), 130 ms to 32 ms (providers).
- `_with_free_room` and `SlotEngine.free_slots` look only at periods starting within the longest period before the slot (bisect on sorted starts): same result, no pairwise scan.
- `DjangoSlotStore.replace` deletes stale rows and inserts missing ones instead of rewriting all: 22 ms to ~2 ms.

## p95 of successful requests per endpoint (ms)
| Endpoint | Successes | p95 before | p95 after | E3 |
| --- | --- | --- | --- | --- |
| GET `/api/v1/search/providers` | 482 | 200 | 65 | 99 |
| GET `/api/v1/search/hospitals` | 280 | 160 | 54 | 33 |
| GET `/api/v1/search/specialties` | 284 | 160 | 58 | 50 |
| GET `/` (search page) | 181 | 300 | 140 | 100 |
| GET `/api/v1/providers/{id}` | 285 | 170 | 37 | 30 |
| GET `/api/v1/slots` | 645 | 210 | 70 | 41 |
| POST `/api/v1/booking/holds` | 90 | 130 | 65 | 43 |
| POST `/api/v1/booking/holds/{id}/verify` | 90 | 310 | 110 | 160 |
| POST `/api/v1/appointments` (signed in) | 90 | 250 | 85 | 120 |

"Before" is the first run on the uncommitted E7 tree with the demo stack stopped, so the regression was not noise.

## Failures by code
- None in the final run: all 90 verifications booked an appointment.
- An intermediate run had one `signed-in booking refused: conflict` (a slot taken meanwhile by another virtual user).

## Verdict
- Every p95 of successful requests is under 200 ms.
- Search stays above E3 (page 140 against 100): the room filter probes each department room per candidate slot, the cost of §6.2.
- Verify and signed-in booking are now faster than E3.
