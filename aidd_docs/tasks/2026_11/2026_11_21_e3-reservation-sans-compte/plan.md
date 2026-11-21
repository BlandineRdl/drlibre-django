---
objective: "Un visiteur cherche, choisit un créneau libre et le réserve en validant un code email ; il devient patient sans mot de passe avec une session de 24 h, et la Success Evidence de l'Epic E3 est démontrée."
status: done
---

# Plan: E3 - Un visiteur trouve et réserve un créneau sans compte
Source: GitHub issue #6, `aidd_docs/backlog/epics/un-visiteur-trouve-et-reserve-un-creneau-sans-compte.md` et ses 11 Stories (commentaire de l'issue #6) ; spec §3.1, §4, §5.2–5.5, §6, §7, §12, §14, §16 ; questions ouvertes E3 de `aidd_docs/backlog/open-questions.md`

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | Contexte `booking` : placement, règles, premier disponible sur fakes | [`phase-1.md`](./phase-1.md) | none |
| 2 | Réservation provisoire, code, patient sans mot de passe, session 24 h sur fakes | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Persistance PostgreSQL, limites Redis, emails et expiration Celery, null adapters remplacés | [`phase-3.md`](./phase-3.md) | 2 |
| 4 | Connexion par lien email | [`phase-4.md`](./phase-4.md) | 3 |
| 5 | Recherche publique, filtres, tris, pages publiques | [`phase-5.md`](./phase-5.md) | 3 |
| 6 | Parcours de réservation web et API | [`phase-6.md`](./phase-6.md) | 4, 5 |
| 7 | Seed de charge, Locust, parcours end-to-end, documentation | [`phase-7.md`](./phase-7.md) | 6 |

## External sources
| URL | What it settled |
| --- | --- |
| https://docs.djangoproject.com/en/6.1/topics/db/transactions/#performing-actions-after-commit | `transaction.on_commit` queues the email task only once the booking commits; in tests `captureOnCommitCallbacks` runs the callbacks |
| https://docs.celeryq.dev/en/stable/userguide/tasks.html#retrying | `autoretry_for`, `retry_backoff`, `max_retries` for the email task; `app.send_task(name)` enqueues by name, so notifications infrastructure never imports `interfaces.jobs` |
| https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html | `beat_schedule` entry every 60 s for hold expiry, next to the existing heartbeat |
| https://www.rfc-editor.org/rfc/rfc5545 | `.ics` written by hand: `VCALENDAR`/`VEVENT` with `UID`, `DTSTAMP`, `DTSTART`/`DTEND` in UTC (`Z`), CRLF line ends; no library added |
| https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition | browser-only position for the distance sort; needs a secure context, which `localhost` is; no external service |
| https://docs.locust.io/en/stable/writing-a-locustfile.html | `HttpUser` tasks for search and booking; p95 read from the run's statistics |
| https://mailpit.axllent.org/docs/api-v1/ | `GET /api/v1/messages` and `GET /api/v1/message/{ID}` read the code in e2e and Locust |

## Impact
| Category | Verdict and evidence | Handled in |
| --- | --- | --- |
| Runtime | Redis (rate limits), Celery worker and beat (emails, hold expiry), Mailpit (codes, links): all in the six-service compose stack (`docker-compose.yml`); Locust is a new dev dependency, unverified until installed | 3, 7 |
| Regression | medium: `/` stops redirecting to sign-in and becomes the search (`interfaces/web/views/auth.py::home`, covered by e2e and web tests); the three null adapters (`identity` `NoAppointmentsYet`, `scheduling` `NoAppointmentsYet`, empty appointment dependents of `SchedulingScheduleDependents`) are replaced, covered by existing delete and deactivation scenarios; `FindFreeSlots` and `DjangoSlotQueries` now drop held slots, covered by `tests/features/scheduling/*` and `tests/contracts/`; `GET /slots` opens without session (`tests/api/test_slots_endpoint.py` 401 case changes); no safety-net phase: the existing suite already locks these behaviours | 3, 5 |
| Architecture | starts from six contexts wired by `bootstrap/container.py`; adds `booking` (appointments, holds, codes, placement) and `search` (read side), each a new import-linter layers container with a forbidden contract on its core; scheduling, identity and organisation reach booking only through booking's inbound ports | 1, 3, 5 |
| Documentation | `architecture.md` (contexts, gotchas: holds filtered at read time, null adapters replaced, network limit setting), `codebase-map.md` (booking, search, loadtests), `testing.md` (search scenarios on PostgreSQL), `open-questions.md` (E3 answers), `.env.example` (new settings) | 7 |

## Rules
| Rule | Why it applies |
| --- | --- |
| Hexagonal per context, ports as `typing.Protocol` inherited explicitly, import-linter | two new contexts and new cross-context ports |
| Every write audited in its transaction, metadata ids and `email_domain` only (`AuditEntry._clean`) | hold, code, account, booking, link events (§7.7) |
| Identity from the session, never the body; end time never accepted | §4, §5.2, Story « patient connecté » |
| Responses never reveal whether an email has an account | holds, codes, links (§7.2, §7.3, §7.5) |
| Tests: Gherkin per Story on fakes, Hypothesis for round robin, contract fake vs real, lock test on PostgreSQL, presenters by ViewModel, Playwright + axe, Locust | `aidd_docs/memory/testing.md` |
| Scenario names mirror the Story's acceptance bullets | user memory `test-names-mirror-acceptance` |
| Web views re-render on `invalid_input`, `has_dependents`, `forbidden`; other refusals through `DomainErrorPagesMiddleware` | booking forms show rule and conflict failures inline instead (see Decisions) |
| One-line comments only | user CLAUDE.md |

## Decisions
| Decision | Why |
| --- | --- |
| New context `booking` owns `Appointment`, `BookingHold`, `VerificationCode`, booking rules, round robin and the placement steps shared by every booking path | INSTALL.md lists `booking`; §5.2 says every path runs the same steps |
| New context `search` is a read side: its SQL adapter reads the organisation, scheduling and booking tables directly; its core imports no other context | light CQRS (architecture.md) to hold p95 < 200 ms |
| Search scenarios run with pytest-bdd on PostgreSQL (`integration`), not on fakes | the filtering and sorting rules live in the SQL; a fake holding them would carry business rules (testing.md forbids it) |
| Holds never touch `scheduling_slot`; `FindFreeSlots` and the search SQL drop a slot overlapping an open hold (`expires_at > now`) of the same clinician, the hold extended by the buffer of the slot's type | expiry checked at read time (architecture gotcha): an expired hold frees the slot without any job |
| Booking an appointment rebuilds the clinician's `scheduling_slot` rows in the same unit of work through scheduling's `RefreshSlots`; scheduling reads appointments through `ClinicianAppointments`, now backed by booking | « shown = bookable »; same mechanism as E2 |
| A contract test asserts that search's next slots equal `FindFreeSlots` on the same data, over windows of at most 31 days starting at now + 120 min | §6.2: slots shown are exactly those booking accepts; `FindFreeSlots` caps ranges at 31 days (`MAX_RANGE`) and filters from now only |
| `SlotQueries.free_slots` returns each slot with its clinician (no `distinct` in SQL); `FindFreeSlots` drops held ones, then dedups by start; new scheduling inbound `SlotAvailability` gives `is_free(clinician, type, start, ignoring_hold)` and `free_clinicians(type, start)` for booking | the current `distinct("start")` loses the clinician, so a hold of one clinician could not be removed and round robin had no candidates |
| Organisation gains inbound `RecordRoundRobinAssignment` (sets `last_assigned_at`, no audit of its own: the booking's audit covers it) called by booking inside its unit of work | no organisation write port exists for that field |
| Wiring order in `real_adapters()`: booking queries (no dependencies) first, then scheduling adapters reading them, then booking use cases using scheduling's ports | breaks the booking → scheduling → booking cycle |
| Placement and holds lock the clinician profile with `select_for_update`, and at verification also the patient user row, inside the unit of work | overlap and 3-bookings checks serialised as in E2; proven by a two-transaction PostgreSQL test |
| At hold creation: `not_found`, clinician conflict (appointments and other open holds), `lead_time_too_short`, `type_not_bookable_online`, `outside_availability`; the patient-dependent checks (patient conflict, `too_many_open_bookings`, refused email) run only at verification, then the whole placement runs again | open question 1; checking the patient before the code would reveal the account |
| A second hold for the same email replaces the first, which is released with its code | open question 2; one open hold per email without blocking a visitor who changes slot |
| A resend voids the previous code, issues a new one valid 10 minutes with 5 attempts, and does not extend the hold | open question 3; no hoarding by resending |
| After 5 wrong attempts the code is dead; the hold stays until its expiry and the visitor may ask for a new code | open question 4 |
| A staff or inactive email gets the same code email flow; with the correct code the booking is refused with one generic `forbidden` message, the hold released, no account created | open question 5; refusing earlier would reveal the account |
| Correct code but placement failure: account created, session opened, hold removed, failure shown with the refreshed slots | open question 6, Epic boundary |
| A rate limit hit returns `rule_violation` with rule `too_many_requests`; a sign-in link request over its limit still returns the usual answer and sends nothing | open question 7; §4 has no 429 and the link answer must never vary |
| Holds limited to 3 per hour per email, resends to 3 per hour per email, both also per network address | §7.5 limits holds per email and per network; without it a new hold per minute bypasses the resend limit |
| Network limit: 20 per hour per `REMOTE_ADDR` and per kind (hold, code, link), read from setting `NETWORK_HOURLY_LIMIT` (default 20) so the Locust run can raise it | Epic boundary; localhost has no proxy, `X-Forwarded-For` is not trusted |
| Rate limiter port `RateLimiter` in `shared_kernel`, Redis adapter in `identity/infrastructure` beside `RedisFailedSignIns`, wired for identity and booking | shared kernel already holds cross-context ports (`Clock`, `UnitOfWork`) |
| Hospitals without coordinates come after those with, then name, then id, in the distance sort | open question 8 |
| Time of day on the slot start, half-open: morning [00:00, 12:00), afternoon [12:00, 17:00), evening [17:00, 24:00) in the hospital's time zone | open question 9 |
| In « premier disponible » the code page names the chosen provider | open question 10; public data, chosen at hold creation (Epic) |
| Provider page: week containing today in the hospital's time zone by default, `?week=YYYY-MM-DD`, navigation limited to weeks meeting the 90-day horizon, bad value falls back to this week; hospital page: next slots per provider for the shortest active online type of its department | open question 11; same rule as search results |
| Verification code: 6 digits from `secrets`, stored as HMAC-SHA256 keyed by `SECRET_KEY`; sign-in link token `token_urlsafe(32)` stored as sha256 | §3.1 hashed code; a plain sha256 of 10^6 codes is reversible |
| Session after code or link: 24 h, `extendable=False` (`Session.after_email_proof`) | §12.2 |
| Sign-in link `/sign-in/link?token=…` shows « Continuer »; the POST consumes it and redirects to `/portal/`; the request log keeps `request.path` only and gunicorn writes no access log, so the token never reaches logs | §7.3; `config/middleware.py` logs `path` only, `docker/gunicorn.conf.py` sets no `accesslog` |
| Emails are enqueued on commit by `CeleryEmailOutbox` (`send_task("drlibre.send_email", argsrepr="…", kwargsrepr="…")`, 5 retries with backoff); a send failure changes nothing already committed; the message body crosses the localhost Redis broker, accepted | Epic boundary « emails après validation »; redacted reprs keep codes and link tokens out of worker logs (unverified until the phase 7 log check) |
| Rate-limit keys carry a prefix; tests use their own prefix and flush it; the e2e setup flushes the compose Redis `drlibre:rate:*` keys | every host client shares one `REMOTE_ADDR` behind Docker's published port, so runs would exhaust 20/h |
| Absolute links in emails come from setting `PUBLIC_BASE_URL` (default `http://localhost:8000`) | emails need absolute sign-in URLs; no request in a Celery task |
| `.ics` written by hand in a presenter; confirmation links to `/portal/` (E1 placeholder until E4) | no new dependency; patient list is E4 |
| `/` is the search for everyone; the nav keeps « Mon espace » for a signed-in user | §6: the landing page is the search |
| API stays cookie-based: `POST /appointments` uses the session identity; bearer tokens remain for the FHIR Epic | §14 says « Signed in »; no token scheme exists yet |
| Locust booking scenario reads codes from Mailpit's API; signed-in booking measured on `POST /appointments` | p95 on the real flow without a back door |
