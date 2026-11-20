---
status: done
---

# Instruction: Identity: password sign-in, sessions, access, password change
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/identity/
│   ├── domain/
│   │   ├── user.py                        ✅  User, Role, Email (lower case), password policy 10-72
│   │   └── session.py                     ✅  Session lifetime 12 h admin / 7 d others, extend under half
│   ├── application/
│   │   ├── access.py                      ✅  ownership guard: not_found / forbidden
│   │   ├── ports/inbound.py               ✅  SignIn, SignOut, AuthenticateSession, ChangePassword
│   │   ├── ports/outbound.py              ✅  Users, Sessions, PasswordHasher, FailedSignIns, TokenGenerator
│   │   └── use_cases/
│   │       ├── sign_in.py                 ✅  same message and one hash verify for unknown email
│   │       ├── sign_out.py                ✅
│   │       ├── authenticate_session.py    ✅  inactive user or expired → none; extends
│   │       └── change_password.py         ✅  clears must_change_password
│   └── infrastructure/
│       ├── django/{apps,models}.py        ✅  UserRecord, SessionRecord (token_hash)
│       ├── django/migrations/0001_initial.py ✅
│       ├── repositories.py                ✅  DjangoUsers, DjangoSessions
│       ├── password_hasher.py             ✅  DjangoPasswordHasher (Argon2)
│       ├── failed_sign_ins.py             ✅  RedisFailedSignIns
│       └── tokens.py                      ✅  SecretsTokenGenerator
├── src/drlibre/interfaces/
│   ├── web/
│   │   ├── auth.py                        ✅  SessionMiddleware, require_role, password-change gate
│   │   ├── views/auth.py                  ✅  sign-in, sign-out, change password
│   │   ├── views/areas.py                 ✅  console, workspace, portal homes
│   │   ├── presenters/auth.py             ✅  form ViewModels
│   │   └── templates/{auth,areas}/*.html  ✅
│   └── api/auth.py                        ✅  POST /auth/login, /auth/logout
├── config/settings.py                     ✏️  identity app, middleware
├── src/drlibre/bootstrap/container.py     ✏️
└── tests/
    ├── features/identity/{sign_in,lockout,access,change_password}.feature ✅
    ├── use_cases/identity/test_*.py       ✅
    ├── fakes/{users,sessions,password_hasher,failed_sign_ins,tokens}.py ✅
    ├── contracts/test_{users,sessions,password_hasher,failed_sign_ins}.py ✅
    ├── presenters/test_auth_presenters.py ✅
    └── api/test_auth_endpoints.py         ✅  integration: login, logout, areas, 403, redirect
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | fake container with an admin, a clinician, a patient with password, an inactive user | users ready | system |
| Happy path | admin signs in on `/sign-in` | lands on `/console/`; session lasts 12 h; success audited with email domain only | browser |
| Happy path | clinician and patient sign in | `/workspace/` and `/portal/` (empty home) | browser |
| Happy path | `POST /api/v1/auth/login` then `/logout` | 200 `{role, home}` with cookie, then 204 and session row deleted | api |
| Edge case | unknown email, wrong password | same message, both run one hash verify | browser |
| Edge case | inactive user signs in | refused with the same message | browser |
| Edge case | 10 failures in 15 min, then the right password | refused until the window passes; lockout audited; success clears the count | system |
| Edge case | session with less than half its life left is used | extended to a full lifetime | system |
| Edge case | no session opens `/console/` | redirect to `/sign-in?next=/console/` | browser |
| Edge case | clinician opens `/console/` | 403 forbidden page | browser |
| Edge case | guard on an absent record, on a record owned by another user | `not_found`, `forbidden` | system |
| Edge case | sign-in POST and admin write POST with a foreign `Origin` | `forbidden`, nothing written (scenario in `access.feature`) | api |
| Edge case | user with `must_change_password` opens their area | sent to `/account/password` | browser |
| Edge case | change with wrong current, same, 9 or 73 characters | `invalid_input` on the field; nothing audited | browser |
| Edge case | patient without password | no change-password link, `/account/password` → 403 | browser |
| Teardown | flush DB, clear Redis test keys | baseline restored | system |

## Wireframe
```txt
┌───────────────────────────────────────┐
│ (1) Header: DrLibre                   │
├───────────────────────────────────────┤
│ (2) Se connecter                      │
│   (3) [ error summary, role=alert ]   │
│   Email     [______________________]  │
│   Mot de passe [___________________]  │
│   (4) [ Se connecter ]                │
└───────────────────────────────────────┘
┌───────────────────────────────────────┐
│ (1) Header: DrLibre · (5) Déconnexion │
├───────────────────────────────────────┤
│ (6) Changer mon mot de passe          │
│   Mot de passe actuel [____________]  │
│   Nouveau (10 à 72) [______________]  │
│   (7) [ Enregistrer ]                 │
└───────────────────────────────────────┘
```
1. Header: brand; area nav once signed in.
2. Sign-in form, labelled fields.
3. Error summary tied to fields, focus on first invalid.
4. Submit.
5. Sign-out as a POST form button.
6. Password change form, also the forced first-sign-in step.
7. Submit.

## Tasks to do
### `1)` Domain and ports
> Users, sessions and their rules in pure Python.

1. `Role` StrEnum, `User`, `Email`, password length policy, `Session.issue` / `extended`.
2. Inbound and outbound ports with one-line contracts.

### `2)` Sign-in, sign-out, session authentication
> Password sign-in per §12.1 and sessions per §12.2.

1. `SignInUseCase`: lockout check, verify (dummy hash for unknown), active check, audit success/failure/lockout with domain only, own transaction for failures.
2. `SignOutUseCase`, `AuthenticateSessionUseCase` with extension and inactive cut-off.
3. Django models, repositories, Argon2 hasher, Redis counter; fakes and contracts.

### `3)` Access in the web and API
> One area per role, checked on the server for every request.

1. `SessionMiddleware` resolves the identity from the cookie; `require_role`; redirect and 403; must-change gate.
2. Sign-in, sign-out, area homes, change-password views with presenters.
3. Ninja `auth.py` router: login sets cookie, logout deletes session.
4. `identity/application/access.py` ownership guard (`not_found` / `forbidden`), scenarios in `access.feature`.
5. `access.feature` cross-origin scenario driving the Django client through `SameOriginMiddleware`.

### `4)` Password change
> Temporary passwords do not stay in use.

1. `ChangePasswordUseCase`: current required, new differs, 10-72, audited without the password.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | domain behaviour reached through use-case scenarios only |
| 2 | `sign_in.feature` and `lockout.feature` green on fakes; contracts green on PostgreSQL and Redis |
| 3 | `access.feature` green; integration tests show redirect, 403 and role homes |
| 4 | `change_password.feature` green, forced change enforced |
