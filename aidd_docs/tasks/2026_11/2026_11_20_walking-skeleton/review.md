# Review: walking-skeleton
- Rounds: 1
- Started: 2026-11-20

## Round 1 · r-3244
- Date: 2026-11-20
- By: Black Sun
- Diff: `main...19f8566` plus the working tree (`CLAUDE.md`, uncommitted)
- Axes: code, functional, relevancy
- Verdict: approve
- Score: 17/17 met, 0 unmet, 0 unverified at runtime, 0 out of the diff

### Criteria
- [x] P1.1 `uv sync`, Python 3.13, celery 5.6.x — `uv run python -V` 3.13.14; `uv.lock` celery 5.6.3
- [x] P1.2 Ruff and Pyrefly run with the config — `pyproject.toml:38-52`; pre-commit ruff/pyrefly Passed (checker run on 19f8566)
- [x] P1.3 `manage.py check` passes — `check --deploy` in web container: 0 errors, 3 deploy warnings (checker run)
- [x] P2.1 ten spec 4 codes with HTTP status — `src/drlibre/shared_kernel/errors.py:5-33`, `tests/rules/test_error_codes.py`
- [x] P2.2 BDD passes, no Django in health domain/application — `tests/use_cases/test_health.py`; lint-imports 4 kept
- [x] P2.3 `curl /api/v1/health` 200 JSON — checker run: `HTTP/1.1 200 OK`, `{"status": "ok", "database": "up", ...}`
- [x] P2.4 `uv run pytest` green incl. integration — checker run with compose up: `29 passed`
- [x] P3.1 correlation id echoed or generated — `config/middleware.py:14-31`; checker run echoed `chk-123`
- [x] P3.2 log line JSON with correlation id — `tests/integration/test_http_headers.py:26-36`; web log `"correlation_id": "chk-123"`
- [x] P3.3 CSP `frame-ancestors 'none'` and headers — `config/settings.py:46-50`; response `default-src 'self'; frame-ancestors 'none'`
- [x] P4.1 6 services running — checker run: web, worker, beat, postgres, redis, mailpit running
- [x] P4.2 heartbeat JSON line within 90 s — worker log `"event": "heartbeat"` with `correlation_id`, ~60 s after start
- [x] P4.3 Mailpit receives the test message — `tests/integration/test_mailpit.py` passed; `localhost:8025` 200
- [x] P4.4 seed twice exit 0; HTMX 2.0.x — second `python -m scripts.seed` exit 0; `version:"2.0.11"`
- [x] P5.1 `lint-imports` passes on clean code — 4 kept, 0 broken
- [x] P5.2 `pre-commit run --all-files` passes — all five hooks Passed
- [x] P5.3 failure names the contract; memory lists gates — trial: `drlibre.health.domain is not allowed to import django`, `drlibre.interfaces is not allowed to import drlibre.health.infrastructure`; `aidd_docs/memory/coding-assertions.md`

### Findings
- `config/settings.py:38` : no `CsrfViewMiddleware`; `check --deploy` raises security.W003, and the architecture gotcha says anonymous POSTs need an explicit check → add `django.middleware.csrf.CsrfViewMiddleware` now so the first form or POST route starts protected — 🟢 minor, security
- `src/drlibre/health/infrastructure/system_clock.py:6` : the adapter of the shared-kernel `Clock` lives in the `health` context, so the next context must import `health.infrastructure` or copy it → move `SystemClock` to a shared adapter home (stdlib only, so `shared_kernel` can hold it) — 🟢 minor, architecture
- `tests/conftest.py:35` : the `MAILERS` dict repeats `config/settings.py:75-80` → build it once (a helper in `config/settings.py`) and reuse it in the fixture — 🟢 minor, rot
- `tests/contracts/test_database_probe.py:18` : the contract covers only the up case; `DjangoDatabaseProbe`'s `DatabaseError -> False` path is never held against the fake → add a down case for the real adapter (e.g. a closed or misconfigured connection) — 🟢 minor, code-health
- `tests/integration/test_http_headers.py:12` : sits in `integration/` but uses fakes, no marker and no backend, against `testing.md` layers → move it to `tests/api/` — 🟢 minor, conform
- `CLAUDE.md:66` : commit 5158ffd drops the `aidd_docs/backlog/` memory pointer, outside the brief; the working tree holds an uncommitted edit re-adding it plus `aidd_docs/tasks/` → decide which block is intended and commit it apart from the skeleton — 🟢 minor, fit
