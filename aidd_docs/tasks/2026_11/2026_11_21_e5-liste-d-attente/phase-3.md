---
status: done
---

# Instruction: Notifications et emails « Créneau proposé » et « Créneau réservé »
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/notifications/
│   ├── domain/notification.py                                   ✏️  `WAITLIST_OFFERED`, `WAITLIST_BOOKED` kinds and events; `appointment_id: Id | None`
│   ├── application/ports/inbound.py                             ✏️  `Notify.execute(..., appointment_id: Id | None)`
│   └── application/use_cases/notify.py                          ✏️
├── src/drlibre/booking/
│   ├── application/ports/outbound.py                            ✏️  `BookingNotices.waitlist_offered(entry, start, clinician_id)`, `waitlist_booked(appointment)`
│   ├── infrastructure/outbox_notices.py                         ✏️
│   └── infrastructure/emails.py                                 ✏️  `WAITLIST_OFFERED`, `WAITLIST_BOOKED` wording
└── tests/
    ├── use_cases/notifications/test_appointment_notices.py      ✏️
    └── contracts/test_notifications.py                          ✏️  row without appointment
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | fake world with a patient and a venue | ready | system |
| Happy path | `waitlist_offered` | in-app « Créneau proposé », body the local time only, no appointment link; one email on commit with time, hospital, provider and only the sign-in link | system |
| Happy path | `waitlist_booked` | in-app « Créneau réservé » linked to the new appointment; one email | system |
| Edge case | unit of work rolled back | no row, no email | system |
| Teardown | fakes discarded | baseline | system |

## Tasks to do
### `1)` Kinds and optional appointment
> Spec §11 rows for the waitlist.

1. Add both kinds and events with French titles and body templates; make `appointment_id` optional through `Notification.for_event` and `Notify`; existing callers unchanged.

### `2)` Booking notices
> Same pattern as `cancelled`.

1. `waitlist_offered` and `waitlist_booked` write the in-app row and queue the email through `emails.appointment_email`; subjects « Un créneau vous est proposé », « Votre créneau est réservé ».

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | contract green with and without appointment; body never holds a name, reason or email |
| 2 | each notice writes one row and queues one email; email holds no reason and one link to `/sign-in` |
