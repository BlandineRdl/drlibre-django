---
status: pending
---

# Instruction: Offre automatique à l'annulation et offre manuelle
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/booking/
│   ├── application/ports/inbound.py                             ✏️  `OfferCancelledSlot`
│   ├── application/ports/outbound.py                            ✏️  `Appointments.cancelled_of_type(appointment_type_id, after, earliest, latest)`
│   ├── application/use_cases/waitlist_offers.py                 ✅  `WaitlistOffers.offer_freed(appointment)` shared helper, as `Placement`
│   ├── application/use_cases/cancel_appointment.py              ✏️  calls `offer_freed` in its unit of work
│   ├── application/use_cases/offer_cancelled_slot.py            ✅  admin manual offer
│   └── infrastructure/repositories.py                           ✏️  `cancelled_of_type`
├── src/drlibre/bootstrap/container.py                           ✏️  `offer_cancelled_slot`; `WaitlistOffers` into cancel
└── tests/
    ├── fakes/booking.py                                         ✏️  `cancelled_of_type`
    ├── contracts/test_booking_repositories.py                   ✏️  `cancelled_of_type`
    ├── features/booking/{un_creneau_annule_est_propose_au_patient_en_attente_le_plus_ancien,l_admin_propose_un_creneau_annule_a_une_entree_en_attente}.feature ✅
    ├── use_cases/booking/{test_un_creneau_annule_est_propose_au_patient_en_attente_le_plus_ancien.py,test_l_admin_propose_un_creneau_annule_a_une_entree_en_attente.py} ✅
    └── integration/test_concurrent_waitlist_offers_postgres.py  ✅  two cancels, one oldest entry: one offer; lock waiter seen
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | fake world: two `WAITING` entries of other patients for the type (older and newer, one preferring another clinician), the patient's own entry, a `BOOKED` appointment of the cancelling patient | ready | system |
| Happy path | patient cancels | oldest matching entry `OFFERED`, linked to the cancelled appointment; « Créneau proposé » with email; audit `booking.waitlist_offered`; slot still free for anyone | system |
| Edge case | equal `created_at` | lowest id wins | system |
| Edge case | entries of another type, other preferred clinician, window not containing the slot, `EXPIRED`, own entry | none offered; nothing changes | system |
| Happy path | admin manual offer on a `WAITING` entry | first future cancelled appointment of the type in the window, clinician still free, not held by another offer → `OFFERED` with notice and audit | system |
| Edge case | manual offer: no suitable slot; entry not `WAITING`; slot already offered to another entry; non-admin | `not_found`; `invalid_transition` with status; skipped to the next slot or `not_found`; `forbidden` | system |
| Teardown | fakes discarded | baseline | system |

## Tasks to do
### `1)` Automatic offer
> Spec §5.8 in the cancel's transaction.

1. `WaitlistOffers.offer_freed(appointment)`: `candidates_locked` (type, clinician, start, end, excluding the appointment's patient), `oldest`, `offered`, `save`, audit `booking.waitlist_offered` (`appointment_id`), `notices.waitlist_offered`; no candidate does nothing.
2. Call it in `CancelAppointmentUseCase` after `slot_refresh.refresh`, before `notices.cancelled`.

### `2)` Manual offer
> Admin offers the first suitable cancelled slot.

1. `OfferCancelledSlotUseCase.execute(actor_id, entry_id)`: `Staff.is_admin` else `forbidden`; `get_locked`, `WAITING` else `invalid_transition`; scan `cancelled_of_type` by start then id, keep the first matching the preferred clinician, `FreeSlots.is_free`, and not `holds_offer`; none `not_found`; offer, save, audit actor the admin, notice.

### `3)` Story scenarios and race
> Stories « proposé au plus ancien », « l'admin propose ».

1. One scenario per acceptance bullet.
2. PostgreSQL race per `testing.md`: two cancels of slots matching one entry; one offer; fails with the candidate lock removed.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | a refused cancel offers nothing; existing cancel scenarios unchanged |
| 2 | refused offers write, notify and email nothing |
| 3 | each acceptance bullet maps to a scenario name; race test sees a `Lock` waiter |
