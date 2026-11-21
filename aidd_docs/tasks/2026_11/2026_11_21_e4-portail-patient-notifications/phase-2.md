---
status: pending
---

# Instruction: Notifications in-app et « RDV réservé »
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/
│   ├── notifications/
│   │   ├── domain/notification.py                               ✅  `Notification`, `NotificationKind`, `for_event` building title and time-only body
│   │   ├── application/ports/inbound.py                         ✅  `Notify`, `ListNotifications`, `MarkNotificationRead`, `CountUnread`
│   │   ├── application/ports/outbound.py                        ✏️  `Notifications` store (`add` returning created, `page_for`, `get`, `save`, `unread_count`)
│   │   ├── application/use_cases/{notify,list_notifications,mark_notification_read,count_unread}.py ✅
│   │   └── infrastructure/
│   │       ├── repositories.py                                  ✅  `DjangoNotifications`; reminder insert with conflict ignored
│   │       └── django/{apps.py,models.py,migrations/0001_initial.py} ✅  `NotificationRecord`, index (recipient, created), partial unique reminder index
│   ├── booking/
│   │   ├── application/ports/outbound.py                        ✏️  `BookingNotices.booked/rescheduled/cancelled/reminded`
│   │   ├── application/use_cases/placement.py                   ✏️  `notices.booked` in the unit of work
│   │   └── infrastructure/{outbox_notices.py,emails.py}         ✏️  in-app row through `Notify`, emails for reschedule, cancel, reminder
│   └── bootstrap/container.py                                   ✏️  notifications adapters and use cases; wiring before booking
├── config/settings.py                                           ✏️  notifications Django app
├── pyproject.toml                                               ✏️  only if a contract must name notifications' core
└── tests/
    ├── features/notifications/le_patient_lit_ses_notifications_et_les_marque_comme_lues.feature ✅
    ├── use_cases/notifications/{conftest.py,test_le_patient_lit_ses_notifications_et_les_marque_comme_lues.py} ✅
    ├── fakes/{notifications.py,world.py}                        ✅✏️
    ├── contracts/test_notifications.py                          ✅  fake vs Django, reminder uniqueness
    └── integration/test_reminder_uniqueness_postgres.py         ✅  two transactions insert one reminder each → one row
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | fake world with a patient, a clinician and a free slot | ready | system |
| Happy path | the patient books | one « RDV réservé » notification, kind schedule changed, body with time only; one email queued (confirmation) | system |
| Happy path | list, then mark one read | newest first, own only; read time set; audit `notification.read` without personal data | system |
| Edge case | mark another patient's notification | `forbidden`; unknown id `not_found` | system |
| Edge case | booking refused | no notification, no email | system |
| Teardown | fakes discarded | baseline | system |

## Tasks to do
### `1)` Notification domain and store
> In-app rows with title and a time-only body.

1. `NotificationKind` (`SCHEDULE_CHANGED`, `APPOINTMENT_CANCELLED`, `APPOINTMENT_REMINDER`), `Notification(id, recipient_id, kind, title, body, appointment_id, created_at, read_at)`.
2. `Notification.for_event(event, at_local, zone_name)` builds French title and body (« Votre RDV du 25/11/2026 à 14:30 (Europe/Paris) ... »); no name, reason or email.
3. Django model, migration, `DjangoNotifications`, fake, contract suite.

### `2)` Notification use cases
> Patient reads and marks; booking writes.

1. `Notify.execute(...) -> bool` adds in the caller's unit of work, `False` when the reminder already exists: the Django adapter inserts in a savepoint and catches the partial index `IntegrityError`; the contract test asserts `True` then `False`.
2. `ListNotifications` (page of 20, newest first, recipient from caller), `MarkNotificationRead` (audited, `forbidden` for another recipient), `CountUnread`.

### `3)` Booking notices
> Every patient event writes its row and queues its email.

1. `BookingNotices` gains `booked`, `rescheduled`, `cancelled`, `reminded(appointment) -> bool`; `OutboxBookingNotices` calls `Notify` then queues the email (none for `booked`, the E3 confirmation stays).
2. `Placement.place` calls `notices.booked` beside `confirmed`.
3. Emails: subject per event, time with named zone, hospital, provider, `{base}/sign-in` link only, no reason.

### `4)` Story scenarios
> Story « Le patient lit ses notifications et les marque comme lues ».

1. One scenario per acceptance bullet, French names verbatim.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | contract suite green on fake and Django; body never holds name, reason or email |
| 2 | Story scenarios green; another patient's notification gives `forbidden` |
| 3 | a booking queues exactly one email and writes one notification; refused booking writes none |
| 4 | each acceptance bullet maps to a scenario name |
