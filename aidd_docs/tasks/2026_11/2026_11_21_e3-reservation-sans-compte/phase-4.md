---
status: done
---

# Instruction: Connexion par lien email
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/identity/
│   ├── domain/sign_in_link.py                             ✅  SignInLink (token hash, patient, expires 15 min, used_at, cancelled), `usable(at)`
│   ├── application/ports/inbound.py                       ✏️  RequestSignInLink, UseSignInLink
│   ├── application/ports/outbound.py                      ✏️  SignInLinks (add, by_token_hash, cancel_open_for, save)
│   ├── application/use_cases/request_sign_in_link.py      ✅  same answer always; only active patients get a link; 3/h per email, 20/h per network; cancels earlier links; audit `identity.link_requested`
│   ├── application/use_cases/use_sign_in_link.py          ✅  consumes once, 24 h session; audit `identity.link_used` or `identity.link_refused`
│   ├── infrastructure/django/models.py                    ✏️  SignInLinkRecord
│   ├── infrastructure/django/migrations/0003_sign_in_link.py ✅
│   └── infrastructure/repositories.py                     ✏️  DjangoSignInLinks
├── src/drlibre/interfaces/
│   ├── api/auth.py                                        ✏️  `POST /auth/link` (always 202 same body), `POST /auth/link/verify` (sets cookie)
│   └── web/
│       ├── views/auth.py                                  ✏️  link request form on sign-in, `/sign-in/link?token=` GET « Continuer », POST consumes → `/portal/`
│       ├── presenters/auth.py                             ✏️  link request and continue ViewModels
│       ├── templates/auth/form_page.html                  ✏️  second form « Recevoir un lien »
│       ├── templates/auth/link_sent.html                  ✅
│       ├── templates/auth/link_continue.html              ✅
│       └── urls.py                                        ✏️
├── src/drlibre/bootstrap/container.py                     ✏️
└── tests/
    ├── features/identity/le_patient_se_connecte_par_un_lien_recu_par_email.feature ✅
    ├── use_cases/identity/test_le_patient_se_connecte_par_un_lien_recu_par_email.py ✅
    ├── contracts/test_sign_in_links.py                    ✅
    ├── api/test_sign_in_link_endpoints.py                 ✅  same response for known and unknown email; verify sets 24 h cookie; reused token refused
    └── presenters/test_auth_presenters.py                 ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | an active passwordless patient, a patient with password, a clinician, an inactive patient | ready | system |
| Happy path | patient asks a link, opens it, presses « Continuer » | lands on `/portal/` without token in the address; 24 h session never extended | browser |
| Edge case | unknown, staff or inactive email | same page message, nothing sent, nothing created | browser, api |
| Edge case | expired, used or cancelled link; 4th link in an hour | no session; same answer, nothing sent | api |
| Edge case | opening the link without pressing the button | link still usable | browser |
| Teardown | rollback, Redis test prefix flushed | baseline | system |

## Wireframe
```txt
┌──────────────────────────────────────────────┐
│ (1) Nav publique                              │
├──────────────────────────────────────────────┤
│ (2) Se connecter                              │
│  Email [__________]  Mot de passe [_______]   │
│  [ Se connecter ]                             │
├──────────────────────────────────────────────┤
│ (3) Patient ? Recevoir un lien de connexion   │
│  Email [__________]  [ Recevoir un lien ]     │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│ (4) Votre lien de connexion                   │
│  [ Continuer ]                                │
└──────────────────────────────────────────────┘
```
1. Public nav: search, sign-in.
2. Existing password form, unchanged.
3. Link request; after submit the same message whatever the email.
4. Continue page: one button posting the token; expired or used link shows a message and the request form.

## Tasks to do
### `1)` Domain and use cases
> One-time 15-minute links for active patients only.

1. `SignInLink`, port, use cases with rate limits and audits (`email_domain` only).
2. Feature file mirroring the Story's acceptance bullets, on fakes.

### `2)` Persistence and interfaces
> Token never logged, consumed only on « Continuer ».

1. Model, migration, repository, contract test.
2. API endpoints and web pages; cookie through `set_session_cookie`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | every acceptance bullet of the Story has a passing scenario |
| 2 | API responses for known and unknown emails are byte-identical; structlog output of the journey contains no token |
