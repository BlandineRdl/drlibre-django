# Run: formulaires Django
## Run 1
- Head: `348e30a`
- Left: none

| Task | Validation | Result |
| --- | --- | --- |
| 1.1 | settings: `django.forms`, `TemplatesSetting`, `LANGUAGE_CODE = "fr"` (ee0f675); `check --deploy` in pre-commit | passed |
| 1.2 | `WebForm` base: `tests/forms/` in `uv run pytest` | passed |
| 1.3 | auth screens: `tests/api/` page tests and e2e sign-in | passed |
| 1.4 | auth form tests `tests/forms/test_auth_forms.py` | passed |
| 2.1 | booking screens (80353f9): page tests and e2e booking journey | passed |
| 2.2 | cancel, notes, profile, waitlist join: page and use case tests | passed |
| 2.3 | `tests/forms/test_booking_forms.py`, `test_portal_forms.py`, `test_workspace_forms.py` | passed |
| 3.1 | reference screens (4c13b11): `tests/api/test_console_reference.py`, FHIR reference writes | passed |
| 3.2 | users, clinicians, waitlist add, console cancel: console page tests, e2e admin journey | passed |
| 3.3 | `tests/forms/test_console_forms.py` | passed |
| 4.1 | `grep -rnE "FieldSpec\|build_form\|FormView\|FieldView\|_form.html\|presenters.forms" src tests` | nothing |
| 4.2 | memory lines in `architecture.md`, `codebase-map.md`, `testing.md` | one line each |
| 4.3 | `uv run pre-commit run --all-files` | all hooks passed |
| 4.3 | `uv run pytest` | 2155 passed, 11 deselected |
| 4.3 | `uv run pytest -m e2e` on the `drlibre-e2e` stack (port 28000) | 11 passed, axe-core at 375 and 1440 px |

## Run 2: review repair
- Head: `e5d1b8b`
- Left: none

| Finding | Validation | Result |
| --- | --- | --- |
| time off parsed in `settings.TIME_ZONE` | `TimeOffForm` start/end are text with the `datetime-local` widget; `test_a_time_off_typed_in_the_hospital_zone_is_left_to_the_use_case` fails on the old form | passed |
| length literals | `PASSWORD_MIN_LENGTH`/`PASSWORD_MAX_LENGTH`, `MAX_TIME_OFF_REASON`, `MAX_FULL_NAME`/`MAX_PHONE`/`MAX_BOOKING_REASON` re-exported by the inbound ports; `uv run lint-imports` | passed |
| unreachable redirect, `.field-error`, empty summary `<ul>` | `test_a_refused_sign_in_shows_its_message_without_an_empty_field_list` fails on the old template | passed |
| `options`/`INVALID` copies | one each in `forms/base.py` | passed |
| forms ↔ presenters imports | `WEEK_ORDER`, `ROLE_LABELS` in `interfaces/web/labels.py` | passed |
| test names | portal and console join tests renamed | passed |
| gates | `uv run pre-commit run --all-files`; `uv run pytest` | all hooks passed; 2157 passed, 11 deselected |
| e2e | `uv run pytest -m e2e` on the `drlibre-e2e` stack (port 28000), removed after | 11 passed |
