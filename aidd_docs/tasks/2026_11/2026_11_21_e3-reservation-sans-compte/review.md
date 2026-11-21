# Review: E3 réservation sans compte
- **Verdict**: changes-requested
- **Diff**: `origin/main...feat/e3-reservation-sans-compte`
- **Axes run**: code, relevancy
- **Date**: 2026_11_21
- **Findings**: 0 critical, 4 warning, 7 minor

## Phases
Not run.

## Findings
| Sev | Kind | Phase | Location | Issue | Fix |
| --- | --- | --- | --- | --- | --- |
| 🟡 warning | code | - | src/drlibre/booking/application/use_cases/placement.py:192-204 | Room choice is not serialised: two clinicians of one department booking the same time each lock only their own profile, both see the room free in `busy_rooms` and both get it (spec 5.2 step 5); no constraint, no concurrent test | Lock the department's active rooms (`ScheduleLocks.lock_rooms`, accepted lock-adapter exception) before `busy_rooms`, prove with a two-transaction PostgreSQL test |
| 🟡 warning | conform | - | src/drlibre/interfaces/web/presenters/booking.py:45, src/drlibre/interfaces/web/presenters/auth.py:14 | "valables 10 minutes" / "valable 15 minutes" hard-coded, breaking rule 0-interfaces-no-business-rule ("never repeat a policy number as a literal, in text") while the emails already derive them | Format from `CODE_LIFETIME` / `LINK_LIFETIME` as `emails.py` does |
| 🟡 warning | conform | - | src/drlibre/booking/application/use_cases/create_hold.py:24, resend_code.py:16, src/drlibre/booking/domain/booking_rules.py:6-7, hold.py:8, verification_code.py:8-9 | Booking policy constants (holds/resends per email, cancellation window, max open online, hold and code lifetimes, attempts) live outside `shared_kernel/booking_policy.py`, contrary to the rule "declare each policy constant once in booking_policy.py" (rule scope ambiguous: all policy or only cross-layer ones) | Move them to `booking_policy.py` or narrow the rule's wording |
| 🟡 warning | fit | - | src/drlibre/booking/application/use_cases/create_hold.py:101-102,131-133; verify_hold.py:72,123 | Replacing or releasing a hold deletes the hold and its code without an audit entry, while expiry writes `booking.hold_expired`; breaks "every write is audited" | Record `booking.hold_released` (email_domain only) in `_release` |
| 🟢 minor | code | - | src/drlibre/booking/application/use_cases/verify_hold.py:88-96 | A matching code is not consumed in its locked transaction: two concurrent correct submits both pass and open two sessions | Delete the code on match inside `_attempt` |
| 🟢 minor | code | - | src/drlibre/booking/application/use_cases/book_appointment.py:36-45, create_hold.py:105 | `first_available` ranks before any lock: concurrent first-available bookings pick the same clinician and the second gets `conflict` although another is free | Lock the ranked candidates, or fall to the next ranked on `conflict` |
| 🟢 minor | rot | - | src/drlibre/booking/application/use_cases/placement.py:214-216 | Email domain re-derived by `rsplit("@")`, duplicating `VisitorDetails.email_domain` / `Email.domain` | Have `Patients` return the domain, or reuse the value object |
| 🟢 minor | rot | - | src/drlibre/booking/application/use_cases/create_hold.py:23-36, src/drlibre/identity/application/use_cases/request_sign_in_link.py:17,46-50 | `HOURLY` and the email+network limit check are written twice | Put one `refuse_over_limit`/window helper in `shared_kernel/rate_limit.py` |
| 🟢 minor | rot | - | src/drlibre/interfaces/web/presenters/search.py:27-28, src/drlibre/search/domain/criteria.py:9-10,75 | Page sizes declared twice (presenter and domain), and `criteria.py:75` falls back to literal `20` instead of `DEFAULT_PAGE_SIZE` | Import from `criteria`, use the constant |
| 🟢 minor | code | - | src/drlibre/interfaces/web/views/booking.py:240,245 | `failure ... else GONE` / `else 409` is unreachable: `VerifiedBooking` always carries a failure when it has no appointment | Model the outcome so one of the two is guaranteed, drop the fallback |
| 🟢 minor | code | - | src/drlibre/booking/application/use_cases/create_hold.py:32, request_sign_in_link.py:47 | Rate-limit keys hold the raw email (`hold:email:<address>`) in Redis | Key on a hash of the email |

## Verification
| Metric | Value |
| --- | --- |
| Verified | Not run |
| Files checked | booking use cases (create_hold, verify_hold, placement, book_appointment, resend_code, expire_holds), booking infrastructure (schedule_locks, repositories, outbox_notices, emails, directory), identity link and patient account use cases, identity repositories, web views booking/auth, api booking, notifications celery_outbox, search sql_queries, presenters booking/auth/search, shared_kernel booking_policy, rules 00/07 |
| Unchecked | Not run |
| Unplanned | Not run |
