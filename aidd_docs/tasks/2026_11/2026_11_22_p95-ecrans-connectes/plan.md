---
objective: "Every signed-in screen and API list named in #23 has a p95 measured by Locust on the load seed, recorded in load-results.md, each p95 >= 200 ms backed by a fix issue."
status: done
---

# Plan: p95 des écrans connectés et du tableau de bord
Source: GitHub issue BlandineRdl/drlibre-django#23

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | Load seed signs in and fills audit and notifications | [`phase-1.md`](./phase-1.md) | none |
| 2 | Locust scenario per signed-in role | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Run, record p95, file fix issues | [`phase-3.md`](./phase-3.md) | 2 |

## External sources
| URL | What it settled |
| --- | --- |
| https://docs.locust.io/en/stable/writing-a-locustfile.html | Several `HttpUser` classes in one file share `-u` by their `weight`; `on_start` runs once per virtual user |

## Impact
| Category | Verdict and evidence | Handled in |
| --- | --- | --- |
| runtime | Load clinicians have no password (`seed_load` creates `UserRecord` without `password_hash`) and sign-in links serve patients only (`request_sign_in_link.py:53`): clinicians cannot sign in until the seed sets a hash; observed in code | 1 |
| runtime | Load seed bulk inserts unaudited rows and no notification: `/console/audit/` and `/portal/notifications` would be measured on near-empty tables; observed in `seed_load` | 1 |
| runtime | `LINKS_PER_EMAIL_PER_HOUR = 3`: each patient virtual user signs in once in `on_start` with a random load patient of 5 000, under the limit; unverified until the run | 2, 3 |
| regression | `scripts/seed.py` load path covered by `tests/integration/test_seed.py:104` for overlaps only, not audit nor notifications; risk low; no safety-net phase, the new inserts get their own test in phase 1 task 4 | 1 |
| runtime | `SameOriginMiddleware` lets a POST without `Origin` pass (`config/middleware.py:63-65`); `/auth/login` and `/auth/link*` are `auth=None`, so no CSRF check; observed | 2 |
| runtime | Lockout counts failures only (`sign_in.py:51,58`); a wrong `LOAD_PASSWORD` would lock the single admin for 15 min: Locust aborts the run on the first sign-in refusal (`environment.runner.quit()`); observed | 2 |
| runtime | Over the per-email link limit `/auth/link` still answers 202 (`request_sign_in_link.py:50-51`): a missing Mailpit token counts as `sign-in refused` and the user stops; observed | 2 |
| regression | `Visitor` class kept as is; its endpoints still measured, now sharing `-u` with the other roles | 2 |
| architecture | none: seed and loadtests sit outside the hexagon | none |
| documentation | `aidd_docs/memory/codebase-map.md` (loadtests line names search and booking only), `aidd_docs/memory/testing.md` (performance row) | 3 |

## Rules
| Rule | Why it applies |
| --- | --- |
| architecture.md Constraints: p95 under 200 ms proven by load tests | The objective |
| testing.md: performance via `./scripts/load-run.sh`, results in the plan's `load-results.md` | Where and how to record |
| coding-assertions.md gates (pre-commit, ruff on new files) | Seed and locustfile are linted Python |
| No personal data in audit metadata | Seeded audit entries carry no name or email |
| One-line comments only (user CLAUDE.md) | All new code |

## Decisions
| Decision | Why |
| --- | --- |
| Load clinicians share one `password_hash` of `DEMO_PASSWORD`, hashed once | 200 hashes would slow the seed; fictitious password, localhost only |
| Patients sign in by link through Mailpit (`POST /api/v1/auth/link`, `/auth/link/verify`) | The real patient path; patients set no password |
| Admin signs in as demo admin `admin@drlibre.localhost` via `POST /api/v1/auth/login` | Only admin of the seed; admin is global, so it reads the whole load set |
| Locust reads env `LOAD_PASSWORD`; `load-run.sh` sets it from `docker compose exec -T web python -c 'from scripts.seed import DEMO_PASSWORD; print(DEMO_PASSWORD)'` after the seed | The literal stays only in `scripts/seed.py` |
| API admin filters send aware datetimes (`from=…T00:00:00+01:00`), console filters send dates | `api/appointments.py:57-58` takes `AwareDatetime`; a bare date is a 422 |
| Seed one audit entry per load appointment and one notification per future BOOKED load appointment | Realistic volumes for the journal and the notifications page |
| One run of `load-run.sh` with all classes; raise `-u`/`-t` only if an endpoint gets < 50 successes | One reproducible command |
