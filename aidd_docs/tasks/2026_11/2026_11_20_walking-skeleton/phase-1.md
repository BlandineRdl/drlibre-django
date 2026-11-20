---
status: pending
---

# Instruction: Project and tooling
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── pyproject.toml            ✅
├── uv.lock                   ✅
├── .python-version           ✅
├── .gitignore                ✏️
├── manage.py                 ✅
├── config/
│   ├── __init__.py           ✅
│   ├── settings.py           ✅
│   ├── urls.py               ✅
│   └── wsgi.py               ✅
└── src/drlibre/
    ├── __init__.py           ✅
    ├── shared_kernel/        ✅
    └── bootstrap/            ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `uv sync` | environment built on Python 3.13 | cli |
| Happy path | `uv run python manage.py check` | no issues | cli |
| Edge case | missing `.env` value | pydantic-settings raises a named validation error | cli |
| Teardown | none | none | cli |

## Tasks to do
### `1)` uv project
> Python 3.13 project with the stack summary dependencies.

1. `uv init`, `.python-version` 3.13, src layout with package `drlibre`.
2. Runtime: django 6.1, django-ninja 1.8, pydantic 2, pydantic-settings, structlog, `celery>=5.6,<5.7`, redis, psycopg[binary], argon2-cffi, gunicorn.
3. Dev: ruff, pyrefly, django-stubs, import-linter, pytest, pytest-django, pytest-bdd, hypothesis, pre-commit, python-doctor.
4. `.gitignore`: `.venv/`, `.env`, `__pycache__/`, `.pytest_cache/`, `staticfiles/`.

### `2)` Tool config in pyproject
> Ruff, Pyrefly, import-linter and pytest configured in one file.

1. Ruff lint + format, rule sets incl. `DJ`, target py313.
2. Pyrefly with django-stubs, `src` and `config` searched.
3. import-linter root packages `drlibre`, contracts filled in phase 5.
4. pytest: `DJANGO_SETTINGS_MODULE=config.settings`, `pythonpath = ["src", "."]`, markers `integration`.

### `3)` Settings and Django entry
> Django boots from pydantic-settings.

1. `config/settings.py`: a `Settings(BaseSettings)` reading `.env`: `SECRET_KEY`, `DEBUG`, `DATABASE_URL`, `REDIS_URL`, `EMAIL_HOST`, `EMAIL_PORT`, `DEFAULT_TIME_ZONE` (Europe/Paris), `ALLOWED_HOSTS`.
2. Django settings derived from it; `USE_TZ = True`.
3. `manage.py`, `config/urls.py` (empty api mount point), `config/wsgi.py`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `uv sync` succeeds; `uv run python -V` prints 3.13; celery resolves to 5.6.x |
| 2 | `uv run ruff check .` and `uv run pyrefly check` run with the config |
| 3 | `uv run python manage.py check` passes with a filled `.env` |
