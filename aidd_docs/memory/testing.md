# Testing
## Layers
| Change | Test |
| --- | --- |
| A use case or business behaviour | Gherkin scenario run with pytest-bdd on in-memory fakes |
| A domain rule with many edge cases, such as slots or round robin | Behaviour-level test with Hypothesis properties, never its internal functions |
| A presenter or ViewModel | Unit test of the ViewModel the template renders |
| Search filters and sorts | Gherkin scenario run with pytest-bdd on PostgreSQL (`integration`): the rules live in the SQL |
| A port or adapter | Contract suite run against the fake and the real adapter |
| An ORM, SQL, mail or Redis adapter | Integration test on PostgreSQL, Mailpit or Redis |
| The FHIR API | FHIR R4 contract test |
| A concurrent write guarded by a lock | PostgreSQL test with `django_db(transaction=True)`, one thread per writer closing its connections; the first writer waits until `pg_stat_activity` shows a `Lock` waiter; it must fail with the lock removed |
| A user journey | A few Playwright end-to-end tests |
| Search or booking performance | Locust on the load seed: `uv run python -m scripts.seed --size load` (reseed: `docker compose down -v`, then `up`), `NETWORK_HOURLY_LIMIT=100000` in `.env`, recreate web and worker, then `uv run locust -f loadtests/locustfile.py --headless -u 20 -r 5 -t 2m --host http://localhost:8000`; restore `.env`; results in the plan's `load-results.md` |

## Conventions
- Test behaviour, not functions: a refactoring that keeps behaviour breaks no test.
- No mocks on owned ports; in-memory fakes implement them, with trivial behaviour and no business rule.
- Contract tests keep each fake identical to its real adapter.
- Rate limits: the autouse `rate_limit_prefix` fixture gives each test its own Redis prefix (`settings.RATE_LIMIT_PREFIX`) and flushes it; e2e flushes the compose `drlibre:rate:*` keys with `reset_rate_limits()`.
- Time comes from the `Clock` port; test data comes from hand-written builders.
- Unowned services are tested through their real adapter in integration.
- Inside a transaction `pg_stat_activity` is a frozen snapshot: call `pg_stat_clear_snapshot()` before each read.
- pytest-bdd silently replaces a `Scenario Outline` by another of the same name: keep scenario names unique.
- Mutation testing with mutmut measures test quality instead of coverage.
