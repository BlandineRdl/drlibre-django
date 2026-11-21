# Run: E5 - Les créneaux libérés sont proposés aux patients en liste d'attente

## Run 1

- Head: `aae6a96`
- Left: plan statuses and `assert.md` round 3 uncommitted while validations ran; console add form reuses `console/form.html` instead of a new `console/waitlist_form.html`; the patient nav link « Liste d'attente » is not marked current, like the other nav links

| Task | Validation | Result |
| ---- | ---------- | ------ |
| 1.1 | `WaitlistEntry` guards and transitions, `tests/properties/test_waitlist_entry.py`, `uv run pytest` | passed in the full suite (1146 passed) |
| 1.2 | `Waitlist` contract on fake and Django, guards on PostgreSQL, `uv run pytest tests/contracts tests/integration` | passed in the full suite |
| 1.3 | type time zone and waitlist dependents in organisation scenarios, `uv run pytest` | passed in the full suite |
| 2.1 | Story scenarios « le patient s'inscrit », « l'admin inscrit un patient », `uv run pytest tests/use_cases/booking` | passed in the full suite |
| 2.2 | `SqlWaitlistQueries` contract and admin list scenarios on PostgreSQL, `uv run pytest` | passed in the full suite |
| 2.3 | one scenario per acceptance bullet, API bullets in phase 7, `uv run pytest` | passed in the full suite |
| 3.1 | « Créneau proposé » and « Créneau réservé » kinds, optional appointment, notifications contract, `uv run pytest` | passed in the full suite |
| 3.2 | waitlist notices write in-app and queue emails, `tests/use_cases/notifications`, `uv run pytest` | passed in the full suite |
| 4.1 | automatic offer in the cancel transaction, race test sees a `Lock` waiter, `uv run pytest` | passed in the full suite |
| 4.2 | manual offer Story scenarios, `uv run pytest` | passed in the full suite |
| 4.3 | Story scenarios and concurrent offers on PostgreSQL, `uv run pytest` | passed in the full suite |
| 5.1 | `Placement.place` staff mode and `announce=False`, booking scenarios unchanged, `uv run pytest` | passed in the full suite |
| 5.2 | accept Story scenarios, conflict puts the entry back `WAITING`, `uv run pytest` | passed in the full suite |
| 5.3 | concurrent accept race on PostgreSQL, `uv run pytest` | passed in the full suite |
| 6.1 | expiry and lapse scenarios, `uv run pytest` | passed in the full suite |
| 6.2 | beat entry `expire-waitlist` every 60 s, expiry on PostgreSQL, `uv run pytest` | passed in the full suite |
| 6.3 | one scenario per acceptance bullet, `uv run pytest` | passed in the full suite |
| 7.1 | presenter tests on each status, no time without its zone, `uv run pytest tests/presenters/test_waitlist_presenters.py` | 10 passed |
| 7.2 | portal pages for a passwordless patient, accept only when allowed, `uv run pytest tests/api/test_waitlist_pages.py` | 8 passed |
| 7.3 | console filters fall back, non-admin 403, offer and accept from the list, same file | passed |
| 7.4 | API tests named after the Story bullets, codes and details as the use cases, `uv run pytest tests/api/test_waitlist_endpoints.py` | 5 passed |
| 8.1 | browser journey, both emails in Mailpit without the reason, axe at 375 and 1440 px, `uv run pytest -m e2e` | 9 passed; a scripted walk of the same journey passed its 8 steps |
| 8.2 | memory and open questions read back against the code | `architecture.md`, `codebase-map.md`, `open-questions.md` updated |
| 8.3 | `uv run ruff check .`, `uv run ruff format --check .`, `uv run lint-imports`, `uv run pre-commit run --all-files`, `uv run pytest`, `uv run pytest -m e2e` | every command exited 0 |
