---
status: done
---

# Instruction: Réservation provisoire, code, patient sans mot de passe, session 24 h sur fakes
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/shared_kernel/rate_limit.py                ✅  `RateLimiter` port: `hit(key, *, limit, window) -> bool`
├── src/drlibre/booking/
│   ├── domain/
│   │   ├── hold.py                                        ✅  BookingHold (clinician, type, period, source, VisitorDetails, email, expires_at 10 min), `is_open(at)`
│   │   ├── visitor_details.py                             ✅  parse full name, birth date, email, phone?, reason?, terms accepted → FieldErrors
│   │   └── verification_code.py                           ✅  VerificationCode (hash, email, purpose, expires 10 min, attempts ≤ 5), `check`
│   └── application/
│       ├── ports/inbound.py                               ✅  (extends phase 1) CreateHold, VerifyHold, ResendCode, ExpireHolds, OpenHolds
│       ├── ports/outbound.py                              ✅  (extends phase 1) Holds, VerificationCodes, CodeIssuer (generate + hash), PatientAccounts, PatientSessions
│       └── use_cases/
│           ├── create_hold.py                             ✅  rate limits, hold checks, replaces the email's open hold, code email, audit `booking.hold_created`
│           ├── verify_hold.py                             ✅  code check, account, session, placement, hold removed; failure after code keeps account and session
│           ├── resend_code.py                             ✅  3 per hour per email, 20 per hour per network, voids previous code
│           └── expire_holds.py                            ✅  deletes expired holds and codes, audits `booking.hold_expired`
├── src/drlibre/identity/
│   ├── domain/user.py                                     ✏️  phone, birth_date, email_verified_at; `User.passwordless_patient`
│   ├── domain/session.py                                  ✏️  `EMAIL_PROOF_LIFETIME` 24 h, `Session.after_email_proof` (not extendable)
│   ├── application/ports/inbound.py                       ✏️  PatientAccounts (resolve_or_create → patient id or refused), OpenPatientSession
│   └── application/use_cases/
│       ├── provide_patient_account.py                     ✅  unknown email creates the passwordless patient, audit `identity.patient_created`; active patient reused unchanged; staff or inactive refused
│       └── open_patient_session.py                        ✅  24 h session for a patient id, returns token and expiry
├── src/drlibre/notifications/application/ports/outbound.py ✏️  `EmailOutbox.queue(EmailMessage)`
├── src/drlibre/booking/application/emails.py              ✅  code and confirmation messages: time in hospital zone, hospital, provider, sign-in page link, no reason
├── src/drlibre/bootstrap/container.py                     ✏️  booking hold use cases, identity patient use cases
└── tests/
    ├── fakes/booking.py                                   ✏️  InMemoryHolds, InMemoryVerificationCodes, FixedCodeIssuer
    ├── fakes/users.py                                     ✏️  new user fields
    ├── fakes/sessions.py                                  ✏️  email-proof sessions
    ├── fakes/rate_limiter.py                              ✅  InMemoryRateLimiter
    ├── fakes/email_outbox.py                              ✅  RecordingEmailOutbox
    ├── fakes/world.py                                     ✏️
    ├── features/booking/
    │   ├── un_visiteur_reserve_un_creneau_en_validant_un_code_recu_par_email.feature   ✅
    │   ├── l_email_saisi_rattache_la_reservation_au_bon_patient.feature                ✅
    │   ├── les_reservations_provisoires_et_les_codes_sont_limites.feature              ✅
    │   └── un_visiteur_reserve_le_premier_praticien_disponible.feature                 ✅
    └── use_cases/booking/test_*.py                        ✅  one module per feature above
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | FakeWorld: free slot, online type, `FixedCodeIssuer` returning `123456` | ready | system |
| Happy path | visitor creates a hold then verifies `123456` with an unknown email | passwordless patient created with typed details and verified email; appointment `BOOKED` `ONLINE`; hold gone; 24 h non-extendable session; one code email then one confirmation email; audits with `email_domain` only, actor empty before verification then the patient | system |
| Happy path | first available hold | clinician chosen at hold, named on the hold; last assignment set only at verification; source `ROUND_ROBIN` | system |
| Edge case | same slot asked by a second visitor while held | `conflict`; slot absent from `FreeSlots` until `expires_at` passes on the clock | system |
| Edge case | second hold for the same email | first hold released with its code | system |
| Edge case | 5 wrong codes; code after 10 min; resend ×4 in an hour; 4 holds for one email in an hour; 21 holds from one network address | code refused `invalid_input` on `code` and audited; `rule_violation` `too_many_requests` | system |
| Edge case | existing active patient email; staff or inactive email | booked for that patient, profile unchanged; generic `forbidden`, hold released, nothing created | system |
| Edge case | correct code, slot taken meanwhile | account and session exist, failure returned with refreshed slots | system |
| Edge case | code never entered, clock passes expiry, `ExpireHolds` runs | no appointment, no account, `booking.hold_expired` audited | system |
| Teardown | FakeWorld per scenario | baseline | system |

## Tasks to do
### `1)` Identity: passwordless patient and 24 h session
> A patient without password, opened by proof of email.

1. `User` gains phone, birth date, email verified at; `passwordless_patient(details, at)` with no password and no forced change.
2. `Session.after_email_proof` 24 h, `extendable=False`.
3. `ProvidePatientAccount` and `OpenPatientSession` use cases, audited; inbound ports used by booking's adapters.

### `2)` Holds and codes
> Holds checked at creation, everything checked again at verification.

1. Domain `BookingHold`, `VisitorDetails`, `VerificationCode` (5 attempts, 10 min, purpose `booking`).
2. `CreateHold`: per-email (3/h) and per-network (20/h) limits, hold checks of the plan Decisions under the clinician lock, replace open hold of the email, issue code, queue code email, audit.
3. `VerifyHold`: code check (failure audited `booking.code_failed`), account via `PatientAccounts`, session, `placement` with the hold ignored by `FreeSlots`, remove hold, audit `booking.appointment_booked` with patient actor.
4. `ResendCode` (3/h per email, 20/h per network), `ExpireHolds`, `OpenHolds(clinicians, within, at)` for scheduling.

### `3)` Emails and tests
> One code email, one confirmation email, no sign-in link inside.

1. `EmailOutbox` port; message builders; links only to `{PUBLIC_BASE_URL}/sign-in`.
2. Features in French mirroring each acceptance bullet of the four Stories; fakes trivial.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | passwordless patient has `has_password` false; email-proof session never extends |
| 2 | every scenario of the Test Scope passes on fakes; no response before verification carries patient data |
| 3 | `RecordingEmailOutbox` shows exactly one code email per hold or resend and one confirmation per booking; no body contains the reason or a token link |
