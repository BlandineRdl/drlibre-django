---
objective: "Un patient connecté, avec ou sans mot de passe, retrouve, déplace et annule ses RDV dans les règles, et reçoit une notification in-app et un email pour chaque changement et chaque rappel planifié."
status: implemented
---

# Plan: E4 - Le patient gère ses rendez-vous et reste informé
Source: GitHub issue #7, `aidd_docs/backlog/epics/le-patient-gere-ses-rendez-vous-et-reste-informe.md` et ses 8 Stories (commentaire de l'issue #7) ; spec §3.1, §4, §5.3, §5.6, §5.7, §7.4, §7.6, §8, §11, §12.3, §14, §16, §17 ; questions ouvertes E4 de `aidd_docs/backlog/open-questions.md`

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | Statuts sans `CONFIRMED`, champs d'annulation, garde-fous PostgreSQL | [`phase-1.md`](./phase-1.md) | none |
| 2 | Notifications in-app et « RDV réservé » | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Annulation et déplacement par le patient | [`phase-3.md`](./phase-3.md) | 2 |
| 4 | Job de rappel planifié | [`phase-4.md`](./phase-4.md) | 2 |
| 5 | Lecture des RDV du patient, `GET /appointments`, profil | [`phase-5.md`](./phase-5.md) | 1 |
| 6 | Portail patient web et API d'annulation et de déplacement | [`phase-6.md`](./phase-6.md) | 3, 4, 5 |
| 7 | Parcours end-to-end, documentation, gates | [`phase-7.md`](./phase-7.md) | 6 |

## External sources
| URL | What it settled |
| --- | --- |
| https://docs.djangoproject.com/en/6.1/ref/contrib/postgres/constraints/#exclusionconstraint | `ExclusionConstraint(expressions=[(TsTzRange("start", "end", RangeBoundary()), RangeOperators.OVERLAPS), ("clinician", RangeOperators.EQUAL)], condition=~Q(status__in=...))`; needs `BtreeGistExtension` for `=` on uuid |
| https://docs.djangoproject.com/en/6.1/ref/contrib/postgres/operations/#btreegistextension | `BtreeGistExtension()` operation in the booking migration, before the constraint |
| https://docs.djangoproject.com/en/6.1/ref/models/constraints/#uniqueconstraint | partial `UniqueConstraint(fields=["appointment_id"], condition=Q(kind="APPOINTMENT_REMINDER"))` for one reminder per appointment |
| https://docs.djangoproject.com/en/6.1/ref/models/constraints/#checkconstraint | `CheckConstraint(condition=Q(end__gt=F("start")))` and the status / cancellation consistency check |
| https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html#crontab-schedules | `crontab(minute="*/15")` beat entry for reminders |
| https://www.rfc-editor.org/rfc/rfc5545 | `.ics` already written by `presenters/calendar_file.py`; reused unchanged |

## Impact
| Category | Verdict and evidence | Handled in |
| --- | --- | --- |
| Runtime | `django.contrib.postgres` is not in `INSTALLED_APPS` (`config/settings.py:39-48`), added in phase 1; PostgreSQL `btree_gist` ships with the `postgres` image contrib (unverified until the migration runs on compose); Celery beat already runs `expire-booking-holds` (`config/celery.py:13-20`); Mailpit receives the new emails | 1, 4, 7 |
| Regression | medium: removing `CONFIRMED` touches `booking/domain/appointment.py:10`, `scheduling/domain/appointment.py:9`, `scripts/seed.py:293`, `tests/contracts/test_booking_repositories.py:150`, `tests/use_cases/booking/conftest.py:222`; portal assertions `tests/api/test_auth_endpoints.py:149-151` and `tests/api/test_booking_pages.py:110`; `Placement.place` gains the in-app notification (covered by `tests/features/booking/*`); `/portal/` placeholder replaced (`views/areas.py:28`, e2e `test_patient_signs_in_by_link.py` lands there); the new cancellation check would reject existing load-seed `CANCELLED` rows (`scripts/seed.py:293`, no time or reason), handled by the migration backfill; no safety-net phase: these areas are covered by `tests/features/booking/*`, `tests/contracts/test_booking_repositories.py` and the portal API tests above, rerun after each phase | 1, 2, 6 |
| Architecture | `notifications` (today `Mailer` and outbox only) gains the in-app `Notification` domain, ports and Django table; booking reaches it through its outbound `BookingNotices`, whose adapter calls the notifications inbound port; scheduling's `IsSlotFree` and `FindFreeSlots` gain `ignoring_appointment`, computed on the fly by `SlotEngine`; booking gains a SQL read port for the patient's agenda (light CQRS, like search); identity gains `UpdateProfile` | 2, 3, 5 |
| Documentation | `architecture.md` (notifications in-app, reminder beat, exclusion constraint, reschedule ignoring the appointment), `codebase-map.md` (notifications, portal), `open-questions.md` (E4 answers), `testing.md` if a new layer appears, spec untouched | 7 |

## Rules
| Rule | Why it applies |
| --- | --- |
| Hexagonal per context, ports as `typing.Protocol` inherited explicitly, import-linter contracts (`pyproject.toml`) | new notifications ports, new booking and scheduling port methods |
| Every write audited in its transaction, metadata without personal data (`AuditEntry`) | cancel (no reason), reschedule, mark read, profile (field names only), reminder count |
| Notifications created in the event's transaction; emails queued on commit (`CeleryEmailOutbox`) | §4, §11, §7.6 |
| Emails carry time, hospital, provider, never the reason, and link only to the sign-in page | §7.6, decision 9 of §17 |
| Identity from the session, never the body; end time never accepted | §4, §5.2 |
| Domain errors through `DomainError`; web views catch only `invalid_input` and `forbidden` on their forms (rule 6-domain-errors) | cancel reason and profile forms re-render; other refusals shown inline as booking refusals do |
| Templates without business logic, presenters build ViewModels; WCAG 2.2 AA at 375 and 1440 px | §16 |
| Tests: Gherkin per Story on fakes, contract fake vs real, PostgreSQL tests for constraints and SQL reads, presenters by ViewModel, Playwright + axe | `aidd_docs/memory/testing.md` |
| Feature = Story title, each Scenario name = one acceptance bullet in French, no technical labels | user memory `test-names-mirror-acceptance` |
| One-line comments only | user CLAUDE.md |

## Decisions
| Decision | Why |
| --- | --- |
| `CONFIRMED` removed from both status enums; a data migration turns stored `CONFIRMED` into `BOOKED`; the load seed writes `BOOKED` only | Epic decision, §17 |
| A patient cancels a `BOOKED` or `CHECKED_IN` appointment (24 h rule applies); `COMPLETED`, `CANCELLED`, `NO_SHOW` give `invalid_transition` with the current status | open question 1; §5.6 transition table allows `CHECKED_IN`→`CANCELLED`, Story lists the refused statuses |
| Another patient's appointment or notification gives `forbidden`, an unknown id `not_found` | open question 2; §12.3, same as `ViewAppointmentUseCase` |
| Rescheduling a non-`BOOKED` appointment gives `invalid_transition` with its current status, checked before the rules | open question 3 |
| `.ics` keeps the existing `calendar_file` content: UID, UTC start and end, `SUMMARY` type and provider, `LOCATION` hospital and address, never the reason | open question 4; presenter already tested |
| E4 serves `GET /appointments`, `POST /appointments/{id}/cancel` and `/reschedule` to patients only; clinician and admin callers get `forbidden` until E6 and E7 widen them | open question 5; Epic excludes staff actions |
| The reminder job runs every 15 minutes (`crontab(minute="*/15")`) | open question 6; a reminder lands between 24 h and 23 h 45 before the visit |
| Reminder idempotence: partial unique index on `(appointment_id)` where kind is `APPOINTMENT_REMINDER`; the adapter inserts inside a savepoint (`transaction.atomic()`) and catches the `IntegrityError` of that index to return `False`; the email is queued only on `True` | Epic; two concurrent runs never double-send |
| Notification kinds: `SCHEDULE_CHANGED` (booked, rescheduled), `APPOINTMENT_CANCELLED`, `APPOINTMENT_REMINDER`; French titles « RDV réservé », « RDV déplacé », « RDV annulé », « Rappel de RDV »; body holds only the local time with the named zone | §11; waitlist kinds left to E5 |
| In-app notifications live in the `notifications` context (domain `Notification`, inbound `Notify`, `ListNotifications`, `MarkNotificationRead`, `CountUnread`); booking's `BookingNotices` gains `booked`, `rescheduled`, `cancelled`, `reminded`, each writing the in-app row in the unit of work and queuing the email | one place per concern; booking core still imports no other context |
| « RDV réservé » adds the in-app row only; the E3 confirmation email stays the single booking email | Epic, shadow report decision |
| Cancel and reschedule are booking use cases `CancelAppointmentUseCase`, `RescheduleAppointmentUseCase`; both read the appointment for its clinician, lock clinician then patient (then rooms on reschedule), re-read it under the locks and check status on that copy, save through new `Appointments.save`, rebuild the clinician's slots, audit and notify in one unit of work | architecture lock order; slot table updated in the booking's transaction |
| Reschedule runs `Placement`'s checks with the appointment ignored: `conflicting_resources` and `busy_rooms` gain `excluding: Id | None`; `IsSlotFree` and `FindFreeSlots` gain `ignoring_appointment`, which recomputes that clinician's slots with `SlotEngine` over the requested range without that appointment, then drops held ones | the stored `scheduling_slot` already subtracts the appointment itself; §5.6 « with the appointment itself ignored » |
| Rules order on reschedule: `cancellation_window_closed` (current start), `lead_time_too_short`, `type_not_bookable_online`, `outside_availability`, all listed together; `too_many_open_bookings` not checked | §5.3 « book only » for the count |
| Room on reschedule: current room if free, else the clinician's default room, else the first free active room of the department, else `no_room_available` | Story, §5.6 |
| `BookingRule.CANCELLATION_WINDOW_CLOSED = "cancellation_window_closed"`, using the existing `CANCELLATION_WINDOW`; both moved into `shared_kernel/booking_policy.py` with the other policy numbers | E3 review: policy constants in one place |
| Appointment gains `cancelled_at` and `cancellation_reason` (≤ 500); the reason is required, stripped, empty gives `invalid_input` on `reason` | §3.1, Story |
| PostgreSQL guards: `btree_gist`; exclusion on clinician and on patient with `tstzrange(start, end, '[)')` overlapping where status not in (`CANCELLED`, `NO_SHOW`); checks `end > start` on appointments and holds, status in the five values, `CANCELLED` ⇔ `cancelled_at` and `cancellation_reason` set | Epic; room stays serialised by `lock_rooms`, holds not in the exclusion |
| Migration 0002 backfills stored `CANCELLED` rows with `cancelled_at = start` and reason « Annulé avant E4 » before adding the check | the E3 load seed in an existing volume must migrate without `down -v` |
| `TsTzRange` is a custom `Func(function="TSTZRANGE", output_field=DateTimeRangeField())` in `booking/infrastructure/django/models.py` | Django ships no such expression; the docs' exclusion example defines it |
| API routes keep `auth=None` and read the caller with `identity_of(request)` (set by the session middleware), `unauthenticated` when absent; patient-only routes call `require_patient` so staff get `forbidden` | pattern of `POST /appointments` (`interfaces/api/appointments.py:25`) |
| A constraint violation that slips past the locks surfaces as `conflict` (adapter maps `IntegrityError` of the exclusion to `DomainError(CONFLICT)`) | second defence must not crash into a 500 |
| Patient agenda read through a booking outbound port `PatientAgenda` with a SQL adapter joining booking, organisation and identity tables (clinician name, title, specialty, hospital name, address, time zone, department, room, type) | light CQRS as search; one query per page, p95 kept |
| `GET /appointments` filters `clinician`, `status`, `from`, `to`; a `patient` parameter is accepted and ignored for a patient caller, who always gets only their own | Story « même s'il nomme un autre patient » |
| Profile: identity `UpdateProfileUseCase(user_id, phone, birth_date)`; phone `^[0-9 +()\-]{7,20}$`, birth date ISO real date not after today, empty clears; audit `user.profile_updated` with changed field names; validators in identity's domain, the E3 visitor rule left unchanged | §8 Profile; §7 sets no phone format for holds |
| Portal under `/portal/`: home, `appointments`, `appointments/<id>/cancel`, `appointments/<id>/reschedule?week=`, `appointments/<id>.ics`, `notifications`, `profile`; all `@require_role(Role.PATIENT)`; the existing `/booking/appointments/<id>.ics` stays | §8; nav gains patient links |
| Actions « Annuler » and « Déplacer » shown only when the use case's own pre-checks pass, computed by a booking query `allowed_actions(appointment, now)` from the domain, not in templates | Story « proposée que quand les règles la permettent »; templates hold no rule |
| No Locust run: E4 adds no search or anonymous booking path; the agenda read is one indexed query | p95 constraint proven by E3 load test on search and booking |
