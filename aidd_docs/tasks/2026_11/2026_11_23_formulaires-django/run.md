# Run: formulaires Django
## Run 1
- Head: `348e30a`
- Left: none

| Task | Validation | Result |
| --- | --- | --- |
| 4.1 | `grep -rnE "FieldSpec\|build_form\|FormView\|FieldView\|_form.html\|presenters.forms" src tests` | nothing |
| 4.2 | memory lines in `architecture.md`, `codebase-map.md`, `testing.md` | one line each |
| 4.3 | `uv run pre-commit run --all-files` | all hooks passed |
| 4.3 | `uv run pytest` | 2155 passed, 11 deselected |
| 4.3 | `uv run pytest -m e2e` on the `drlibre-e2e` stack (port 28000) | 11 passed, axe-core at 375 and 1440 px |
