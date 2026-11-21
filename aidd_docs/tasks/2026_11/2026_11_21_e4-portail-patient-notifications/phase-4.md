---
status: pending
---

# Instruction: Job de rappel planifié
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── config/celery.py                                             ✏️  `send-appointment-reminders` every 15 minutes
├── src/drlibre/
│   ├── booking/
│   │   ├── application/ports/inbound.py                         ✏️  `SendReminders`
│   │   ├── application/ports/outbound.py                        ✏️  `Appointments.booked_starting(between)`
│   │   ├── application/use_cases/send_reminders.py              ✅
│   │   └── infrastructure/repositories.py                       ✏️  `booked_starting`
│   ├── interfaces/jobs/tasks.py                                 ✏️  `drlibre.send_appointment_reminders`
│   └── bootstrap/container.py                                   ✏️  `send_reminders`
└── tests/
    ├── features/booking/le_patient_recoit_un_rappel_avant_son_rendez_vous.feature ✅
    ├── use_cases/booking/test_le_patient_recoit_un_rappel_avant_son_rendez_vous.py ✅
    ├── fakes/booking.py                                         ✏️  `booked_starting`
    └── integration/test_reminder_job_postgres.py                ✅  task through the container, beat entry present, two runs one row
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `BOOKED` appointments at +2 h and +23 h, one at +25 h, one `CANCELLED` at +3 h | ready | system |
| Happy path | run the job | two reminders, two emails after commit, one audit entry with count 2 | system |
| Edge case | run again | no new row, no email, no audit entry | system |
| Edge case | appointment of another status or beyond 24 h | no reminder | system |
| Edge case | beat schedule | entry `send-appointment-reminders` with `crontab(minute="*/15")` | system |
| Teardown | fakes or transaction discarded | baseline | system |

## Tasks to do
### `1)` Reminder use case
> Idempotent, audited by count.

1. `SendRemindersUseCase.execute() -> int`: in one unit of work, for each `BOOKED` appointment starting in `(now, now + 24 h]`, `notices.reminded(a)` (row and email only when created); audit `booking.reminders_sent` `{"count": n}` with `actor=None` only when `n > 0`.

### `2)` Schedule
> Runs without an admin.

1. Celery task following `expire_booking_holds`; beat entry every 15 minutes.

### `3)` Story scenarios
> Story « Le patient reçoit un rappel avant son rendez-vous ».

1. One scenario per acceptance bullet.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | two runs create one reminder per appointment; zero-count run leaves no audit |
| 2 | `app.conf.beat_schedule` holds the entry; task runs the use case |
| 3 | each acceptance bullet maps to a scenario name |
