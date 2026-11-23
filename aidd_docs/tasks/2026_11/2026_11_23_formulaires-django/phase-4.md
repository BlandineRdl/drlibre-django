---
status: pending
---

# Instruction: remove the home-grown layer, docs, gates
## Architecture projection
```txt
.
├── aidd_docs/
│   └── memory/
│       ├── architecture.md ✏️
│       ├── codebase-map.md ✏️
│       └── testing.md ✏️
└── src/
    └── drlibre/
        └── interfaces/
            └── web/
                ├── presenters/
                │   ├── choices.py ✅
                │   ├── console_audit.py ✏️
                │   ├── console_appointments.py ✏️
                │   ├── waitlist.py ✏️
                │   └── forms.py ❌
                └── templates/
                    └── _form.html ❌
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d --build` | stack up with the new image | system |
| Happy path | `uv run pytest` then `uv run pytest -m e2e` | full suite and Playwright journeys green, axe-core clean at 375 and 1440 px | cli |
| Edge case | `grep -rnE "FieldSpec|build_form|FormView|FieldView|_form.html|presenters.forms" src tests` | nothing | cli |
| Teardown | `docker compose down` if started for e2e only | baseline restored | system |

## Tasks to do
### `1)` Delete the old layer
> Nothing references it any more.

1. Move `Choice` and `ChoiceView` to `presenters/choices.py`; repoint `presenters/console_audit.py`, `console_appointments.py`, `waitlist.py`.
2. Delete `presenters/forms.py` (`FieldSpec`, `FieldView`, `ErrorView`, `FormView`, `field_messages`, `build_form`) and `templates/_form.html`.

### `2)` Docs
> Memory states the new way.

1. `architecture.md` Gotchas: « Web forms are `django.forms` (`interfaces/web/forms/`, base `WebForm`: ids `field-<name>`, error summary, first-error autofocus, `refuse(DomainError)` → `add_error`); they check input shape, use cases keep validating for API and FHIR; `LANGUAGE_CODE = "fr"`. »
2. `codebase-map.md`: add `interfaces/web/forms/` to the `web/` line.
3. `testing.md` Layers: « A web form | unit test of the bound form in `tests/forms/` ».

### `3)` Contributor checks
> Gates pass on the whole change.

1. `uv run ruff check .` and `uv run ruff format --check .` before staging new files.
2. `uv run pre-commit run --all-files` (Ruff, Pyrefly, import-linter, Python Doctor ≥ 90, `check --deploy`, `makemigrations --check`).
3. `uv run pytest`.
4. `docker compose up -d --build`, `uv run pytest -m e2e`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | the grep of the Test Scope prints nothing |
| 2 | the three memory files state the decision in one line each |
| 3 | pre-commit, full suite and e2e with axe-core pass |
