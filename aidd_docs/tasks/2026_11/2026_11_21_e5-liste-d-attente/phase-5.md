---
status: done
---

# Instruction: Acceptation par le patient et par l'admin
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/booking/
│   ├── application/ports/inbound.py                             ✏️  `AcceptWaitlistOffer`
│   ├── application/use_cases/placement.py                       ✏️  `place(..., actor_id, for_patient, announce=True)`
│   ├── application/use_cases/{book_appointment,verify_hold}.py  ✏️  pass the patient as actor, `for_patient=True`
│   └── application/use_cases/accept_waitlist_offer.py           ✅
├── src/drlibre/bootstrap/container.py                           ✏️  `accept_waitlist_offer`
└── tests/
    ├── features/booking/{le_patient_accepte_un_creneau_propose,l_admin_accepte_une_offre_pour_un_patient}.feature ✅
    ├── use_cases/booking/{test_le_patient_accepte_un_creneau_propose.py,test_l_admin_accepte_une_offre_pour_un_patient.py} ✅
    └── integration/test_concurrent_waitlist_accepts_postgres.py ✅  accept vs booking of the same slot: one `conflict`, entry back to `WAITING`; lock waiter seen
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | fake world: an `OFFERED` entry linked to a cancelled appointment 3 days ahead, slot free | ready | system |
| Happy path | patient accepts own entry | RDV `BOOKED`, offered clinician, type and start, source `ONLINE`; entry `BOOKED`; « Créneau réservé » and its email only; audit `booking.waitlist_accepted` actor the patient | system |
| Happy path | admin accepts | source `STAFF`; staff rules only (start under 120 min accepted); audit actor the admin | system |
| Edge case | patient: start under 120 min, 3 open online bookings, offline type, slot not free | `rule_violation` listing the rules; entry stays `OFFERED`; nothing written | system |
| Edge case | slot booked meanwhile | `conflict` with resources; entry `WAITING`, offer cleared, audit `booking.waitlist_offer_lost` | system |
| Edge case | entry not `OFFERED`; another patient's entry; clinician; unknown id | `invalid_transition` with status; `forbidden`; `forbidden`; `not_found` | system |
| Teardown | fakes discarded | baseline | system |

## Tasks to do
### `1)` Placement for staff
> One placement path for every booking (§5.2).

1. `Placement.place` takes `actor_id`, `for_patient`, `announce`; audit actor `actor_id`; rules through `violations(for_patient=...)`; `announce=False` skips `notices.booked` and `notices.confirmed`.
2. Existing callers pass the patient and `True`; booking scenarios unchanged.

### `2)` Accept use case
> Locks, re-read, placement, entry, notice.

1. `AcceptWaitlistOfferUseCase.execute(actor_id, entry_id)`: read entry and its offered appointment; actor is the entry's patient (`refuse_non_patient`) or an admin (`Staff.is_admin`), else `forbidden`; lock clinician, patient, entry; re-read; `OFFERED` else `invalid_transition`.
2. `Placement.place(source=ONLINE|STAFF, for_patient=..., announce=False)` in the same unit of work; entry `booked()`, save, audit `booking.waitlist_accepted` (`appointment_id`, `source`), `notices.waitlist_booked`.
3. On `conflict`: `back_to_waiting`, save, audit `booking.waitlist_offer_lost`, commit, then raise the same `conflict`.

### `3)` Story scenarios and race
> Stories « le patient accepte », « l'admin accepte ».

1. One scenario per acceptance bullet; API bullets left to phase 7.
2. PostgreSQL race per `testing.md`: accept vs a booking of the same slot; fails with the clinician lock removed.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | all booking features green; admin path skips lead time, open bookings and online rules |
| 2 | only `conflict` changes the entry on a refusal; no « RDV réservé » row on acceptance |
| 3 | each acceptance bullet maps to a scenario name; race test sees a `Lock` waiter |
