---
objective: "Un patient connecté ou un admin inscrit un patient en liste d'attente ; un RDV annulé est proposé à l'entrée la plus ancienne qui correspond, acceptée par le patient ou un admin en un RDV `BOOKED`, et un job planifié expire les entrées et libère les offres échues."
status: implemented
---

# Plan: E5 - Les créneaux libérés sont proposés aux patients en liste d'attente
Source: GitHub issue #8, `aidd_docs/backlog/epics/les-creneaux-liberes-sont-proposes-aux-patients-en-liste-d-attente.md` et ses 9 Stories ; spec §3.1, §4, §5.2, §5.3, §5.8, §8, §10, §11, §7.6, §14, §16, §17 ; questions ouvertes E5 de `aidd_docs/backlog/open-questions.md`

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | Domaine et stockage de la liste d'attente | [`phase-1.md`](./phase-1.md) | none |
| 2 | Inscription par le patient et par l'admin, lectures | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Notifications et emails « Créneau proposé » et « Créneau réservé » | [`phase-3.md`](./phase-3.md) | 1 |
| 4 | Offre automatique à l'annulation et offre manuelle | [`phase-4.md`](./phase-4.md) | 2, 3 |
| 5 | Acceptation par le patient et par l'admin | [`phase-5.md`](./phase-5.md) | 4 |
| 6 | Job d'expiration planifié | [`phase-6.md`](./phase-6.md) | 4 |
| 7 | Écrans portail et console, API | [`phase-7.md`](./phase-7.md) | 5, 6 |
| 8 | Parcours end-to-end, documentation, gates | [`phase-8.md`](./phase-8.md) | 7 |

## External sources
| URL | What it settled |
| --- | --- |
| https://docs.djangoproject.com/en/6.1/ref/models/constraints/#uniqueconstraint | partial `UniqueConstraint(fields=["offered_appointment"], condition=Q(status="OFFERED"))`: one open offer per freed appointment |
| https://docs.djangoproject.com/en/6.1/ref/models/querysets/#select-for-update | `select_for_update()` without `LIMIT`: rows no longer matching after the wait are dropped, the others returned, so candidates are locked as a set and the oldest is picked from the re-read |
| https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html | beat entry every 60.0 s, as `expire-booking-holds` |

## Impact
| Category | Verdict and evidence | Handled in |
| --- | --- | --- |
| Runtime | none new: PostgreSQL, Redis, Celery beat (`config/celery.py:13-22`) and Mailpit already run; migration `booking.0003` after `0002_appointment_guards.py` | 1, 6 |
| Regression | medium: `Placement.place` gains an actor and a staff mode (`placement.py:107-212`, callers `book_appointment.py:38-53`, `verify_hold.py:59`); `CancelAppointmentUseCase` runs the automatic offer in its unit of work (`cancel_appointment.py:37-66`); `Notify` and `Notification.for_event` take an optional appointment (`notifications/application/ports/inbound.py:24`); `dependents_of_type`, `dependents_of_clinician`, `any_for_user` add waitlist entries (`booking/infrastructure/queries.py:38-58`); console route added before the slug catch-all (`interfaces/web/urls.py:57`); no safety-net phase: covered by `tests/features/booking/*`, `tests/use_cases/notifications/*`, `tests/use_cases/organisation/test_organisation.py:154`, `tests/contracts/test_booking_repositories.py`, rerun after each phase | 2, 3, 4, 5, 7 |
| Architecture | booking gains the `WaitlistEntry` aggregate, the `Waitlist` outbound port and its Django table, the SQL read port `WaitlistQueries` (light CQRS, like `PatientAgenda`), the `Staff` outbound port reaching identity's `StaffLookup`; global lock order becomes email, clinician(s), patient, waitlist entries, rooms | 1, 2, 4, 5 |
| Documentation | `architecture.md` (waitlist, lock order, expiry beat, optional notification appointment), `codebase-map.md` (booking waitlist, portal and console pages), `open-questions.md` (E5 answers), rule `6-domain-errors` (waitlist pages), spec untouched | 8 |

## Rules
| Rule | Why it applies |
| --- | --- |
| Hexagonal per context, ports as `typing.Protocol` with one-line docstrings, `<Port>UseCase` with one `execute()` (rule `0-ports-and-use-cases`) | new waitlist ports and use cases |
| Booking reaches identity only through its own port and an adapter named after the context (rule `0-context-boundaries`) | `Staff` → `IdentityStaff` |
| Interfaces decide no role, window or rule; actions offered only when the domain allows them (rule `0-interfaces-no-business-rule`) | accept button, date window, role of the actor |
| Every write audited in its transaction, metadata ids and statuses only | join, offer, accept, lost offer, expiry, lapse |
| Notifications in the event's transaction, emails queued on commit, time hospital provider, never the reason, link to sign-in only (§11, §7.6) | « Créneau proposé », « Créneau réservé » |
| Counters and status read-modify-written under `select_for_update`, re-read after the lock (rule `7-counters-under-lock`) | entry status on offer, accept, expiry |
| Domain errors through `DomainError` (rule `6-domain-errors`) | codes listed in Decisions |
| Value objects frozen with slots, `StrEnum`, `Id`, time from `Clock`, today in the hospital zone (rule `2-python-value-objects`) | entry, status, window |
| Gherkin per Story, scenario names = acceptance bullets, fakes `InMemory*` with contracts (rules `5-acceptance-test-names`, `5-fakes-and-contracts`) | 9 Stories |
| WCAG 2.2 AA at 375 and 1440 px; presenters build ViewModels | portal and console pages |
| One-line comments only | user CLAUDE.md |

## Decisions
| Decision | Why |
| --- | --- |
| `WaitlistEntry(id, patient_id, appointment_type_id, clinician_id: Id \| None, earliest, latest, status, created_at, offered_appointment_id: Id \| None)` in `booking/domain/waitlist.py`; `WaitlistStatus` `WAITING`, `OFFERED`, `BOOKED`, `EXPIRED` | §3.1 |
| The window is given as two dates `from_date`, `to_date` (web and API); the use case turns them into `earliest` = `from_date` 00:00 and `latest` = day after `to_date` 00:00 in the type's hospital zone; a slot fits when `earliest <= start` and `end <= latest` | open question 2 (end inclusive); rule: the window is computed in the use case |
| `to_date` before `from_date`, or `to_date` before today in the hospital zone, gives `invalid_input` on `to_date` | open question 2 |
| A patient may join only for a type bookable online, else `rule_violation` `type_not_bookable_online`; an admin may add any active type | open question 1: an offline type would always fail the patient's acceptance |
| The preferred clinician must be active and of the type's department, else `not_found` | open question 3; §5.2 step 1 |
| `JoinWaitlist.execute(actor_id, appointment_type_id, clinician_id, from_date, to_date, patient_email: str \| None)`: without `patient_email` the actor joins for themself (`refuse_non_patient`: a clinician gets `forbidden`); with it the actor must be an active admin (`Staff.is_admin`), else `forbidden`, and the email must belong to an active patient, else `not_found` | Story « ne peut nommer personne d'autre » and « permet à l'admin de nommer le patient »; the role is decided in the use case, not the router |
| Automatic offer runs inside `CancelAppointmentUseCase`'s unit of work, after the slot refresh; candidates exclude the cancelling patient's own entries | open question 11; §4 one transaction per change |
| Candidates are locked as a set (`Waitlist.candidates_locked`, `select_for_update` in id order, no `LIMIT`), then the oldest (`created_at`, then lowest id) is picked from that re-read | two concurrent cancels never offer one entry twice |
| Manual offer follows the automatic filter (preferred clinician empty or equal), picks the first future cancelled appointment of the type inside the window whose slot `FreeSlots.is_free` still reports free and that no `OFFERED` entry holds; none gives `not_found`; a non-`WAITING` entry gives `invalid_transition` with its status | open question 7 |
| Partial unique index on `offered_appointment` where `status = OFFERED`; its `IntegrityError` becomes `conflict` | two manual offers of one appointment |
| Accepting a non-`OFFERED` entry gives `invalid_transition` with the current status | open question 6 |
| `AcceptWaitlistOffer.execute(actor_id, entry_id)`: the entry's patient accepts with patient rules, source `ONLINE`; an active admin accepts with staff rules, source `STAFF`, actor the admin; anyone else gets `forbidden`, an unknown id `not_found` | Stories; Epic assumption on sources |
| Accept locks clinician, patient, then the entry, re-reads it, then runs `Placement.place` in the same unit of work (both UoWs nest: `DjangoUnitOfWork` keeps a stack, `InMemoryUnitOfWork` a snapshot stack) | lock order email, clinician(s), patient, waitlist entries, rooms |
| On `conflict` the entry goes back to `WAITING` (offer cleared, audit `booking.waitlist_offer_lost`), the change commits, then `conflict` is raised with its resources; on `rule_violation` or `no_room_available` the entry stays `OFFERED` and nothing is written | Epic assumption; open question 4: a later retry may pass (open bookings) and the expiry job frees it at slot start |
| `Placement.place` gains `actor_id: Id` and `for_patient: bool` (audit actor, `booking_rules.violations(for_patient=...)`) and `announce: bool = True`; accept passes `announce=False` and sends only « Créneau réservé » | open question 5: no « RDV réservé » nor booking confirmation email in addition |
| Notification kinds `WAITLIST_OFFERED` « Créneau proposé » and `WAITLIST_BOOKED` « Créneau réservé », body the local time only; `Notify` and `Notification.for_event` take `appointment_id: Id \| None`; the offer notification carries none (the freed appointment belongs to another patient) | §11; spec §12.3 |
| No notification when an offer lapses back to `WAITING` or an entry expires; the status shows in the list | open question 9; §11 lists no such kind |
| Expiry job `ExpireWaitlist` every 60 s (`expire-waitlist` beat entry): `WAITING` with `latest <= now` → `EXPIRED` (`booking.waitlist_expired`); `OFFERED` whose offered start `<= now` → `WAITING`, or `EXPIRED` when `latest <= now` (`booking.waitlist_offer_lapsed`); one audit entry per entry, actor empty | open question 10; Stories audit each change |
| Accept is offered in the portal when `WaitlistEntry.acceptable_by_patient(offered_start, now)` (OFFERED and start at least the lead time ahead), in the console on every `OFFERED` entry whose start is future | rule `0-interfaces-no-business-rule` |
| Admin console accepts on the waitlist list row (« Accepter pour le patient »), offers on `WAITING` rows (« Proposer un créneau »), adds through `/console/waitlist/new` with the patient's email | open question 8 |
| Admin list columns: inscription date, patient name, type, preferred clinician, window, status, offered time with zone; filter `status` (all by default, an unknown value falls back to all), oldest first, 20 per page with total | open question 12; §4 lists |
| Read side `WaitlistQueries` (booking inbound, SQL adapter `SqlWaitlistQueries` joining booking, organisation and identity tables): `own_entries(patient_id)`, `page(status, request)`, `type_options(online_only)`, `clinician_options()` | light CQRS as `PatientAgenda`; one query per page |
| `BookableType` gains `time_zone` (hospital of the department) | today and window in the hospital zone; `Venue.time_zone` needs a clinician, and the preferred one is optional |
| Waitlist entries are dependents of their appointment type, preferred clinician profile and patient user (`dependents_of_type`, `dependents_of_clinician`, `any_for_user`); FK `PROTECT` on type and clinician | §10 deletion table; a delete must give `has_dependents`, never a 500 |
| Web waitlist pages (portal and console) catch `invalid_input`, `rule_violation`, `invalid_transition`, `conflict`, `no_room_available` and, on manual offer, `not_found` inline; rule `6-domain-errors` updated | §4 expected failures are results |
| `POST /waitlist` body `appointment_type_id`, `clinician_id?`, `from_date`, `to_date`, `patient_email?`, unknown fields refused, 201 with the entry; `POST /waitlist/{id}/accept` 201 with the appointment; anonymous `unauthenticated` | §14 |
| Withdrawal of an entry by the patient stays out of scope | shadow report minor point, no Story |
