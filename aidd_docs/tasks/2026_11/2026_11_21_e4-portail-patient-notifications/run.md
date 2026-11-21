# Run: E4 - Le patient gère ses rendez-vous et reste informé
## Run 1
- Head: `6334f3b`
- Left: phase 7 uncommitted while validations ran

| Task | Validation | Result |
| --- | --- | --- |
| 1.1 | `grep -rn CONFIRMED src scripts tests` finds only migrations; full suite green: `uv run pytest` | passed in the full suite (935 passed) |
| 1.2 | domain builds a cancelled appointment with time and reason; rule value `cancellation_window_closed` exists: `uv run pytest` | passed in the full suite (935 passed) |
| 1.3 | contract suite passes on fake and Django for `save` and `excluding`: `uv run pytest` | passed in the full suite (935 passed) |
| 1.4 | each guard test fails with the constraint removed; overlap gives `conflict`; load seed completes: `uv run pytest` | passed in the full suite (935 passed) |
| 2.1 | contract suite green on fake and Django; body never holds name, reason or email: `uv run pytest` | passed in the full suite (935 passed) |
| 2.2 | Story scenarios green; another patient's notification gives `forbidden`: `uv run pytest` | passed in the full suite (935 passed) |
| 2.3 | a booking queues exactly one email and writes one notification; refused booking writes none: `uv run pytest` | passed in the full suite (935 passed) |
| 2.4 | each acceptance bullet maps to a scenario name: `uv run pytest` | passed in the full suite (935 passed) |
| 3.1 | refused statuses give `invalid_transition` with the status; rules listed in spec order: `uv run pytest` | passed in the full suite (935 passed) |
| 3.2 | property green; existing scheduling scenarios unchanged: `uv run pytest` | passed in the full suite (935 passed) |
| 3.3 | refused cancel or reschedule writes, notifies and emails nothing: `uv run pytest` | passed in the full suite (935 passed) |
| 3.4 | each acceptance bullet maps to a scenario name; race test sees a `Lock` waiter: `uv run pytest` | passed in the full suite (935 passed) |
| 4.1 | two runs create one reminder per appointment; zero-count run leaves no audit: `uv run pytest` | passed in the full suite (935 passed) |
| 4.2 | `app.conf.beat_schedule` holds the entry; task runs the use case: `uv run pytest` | passed in the full suite (935 passed) |
| 4.3 | each acceptance bullet maps to a scenario name: `uv run pytest` | passed in the full suite (935 passed) |
| 5.1 | contract green on fake and PostgreSQL; one SQL query per page (`django_assert_num_queries`): `uv run pytest` | passed in the full suite (935 passed) |
| 5.2 | API tests green; another patient's rows never returned: `uv run pytest` | passed in the full suite (935 passed) |
| 5.3 | invalid values give `invalid_input` with the field; audit metadata holds no value: `uv run pytest` | passed in the full suite (935 passed) |
| 5.4 | each acceptance bullet maps to a scenario name: `uv run pytest` | passed in the full suite (935 passed) |
| 6.1 | every page renders for a passwordless patient; actions shown match `allowed_actions`: `uv run pytest` | passed in the full suite (935 passed) |
| 6.2 | API refusals carry the same codes and rules as the use cases: `uv run pytest` | passed in the full suite (935 passed) |
| 6.3 | each acceptance bullet of the 8 Stories maps to a scenario name: `uv run pytest` | passed in the full suite (935 passed) |
| 7.1 | réservé, déplacé, annulé avec notification et email à chaque étape, axe à 375 et 1440 px: `uv run pytest -m e2e` | 8 passed; Mailpit holds booking, reschedule and cancellation emails without the reason; journey also walked in the browser |
| 7.2 | docs name notifications, portal, `FindFreeWeek`, reminder beat, constraints, reschedule, E4 answers | read back |
| 7.3 | `uv run ruff check .`, `uv run ruff format --check .`, `uv run pre-commit run --all-files`, `uv run lint-imports`, `uv run pytest` | all exit 0; 935 passed |
