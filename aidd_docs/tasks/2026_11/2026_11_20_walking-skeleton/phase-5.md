---
status: pending
---

# Instruction: Gates: pre-commit and boundary proof
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── .pre-commit-config.yaml                ✅
├── pyproject.toml                          ✅  import-linter contracts
├── README.md                               ✅  run steps
└── aidd_docs/memory/
    ├── codebase-map.md                     ✏️
    └── coding-assertions.md                ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `uv run pre-commit install` | hooks installed | cli |
| Happy path | `uv run pre-commit run --all-files` | all hooks pass | cli |
| Edge case | add `import django` in `src/drlibre/health/domain/` | `uv run lint-imports` fails naming the contract | cli |
| Teardown | revert the probe import | `lint-imports` passes again | cli |

## Tasks to do
### `1)` import-linter contracts
> Boundaries enforced.

1. Forbidden: `drlibre.*.domain` must not import `django`, `ninja`, `celery`, or any `infrastructure`/`interfaces`/`bootstrap`.
2. Forbidden: `drlibre.*.application` must not import `django`, `infrastructure`, `interfaces`.
3. Forbidden: `drlibre.interfaces` must not import any `*.infrastructure` nor `*.domain` internals beyond what ports expose; it reaches use cases only through `bootstrap`.
4. Layers per context: infrastructure > application > domain.

### `2)` Pre-commit
> Gates run on every commit.

1. Hooks: ruff (lint + format), pyrefly, lint-imports, python-doctor with a minimum score (use its documented hook or a local `uv run` hook).

### `3)` Boundary proof and docs
> Show the contract bites, then record gate commands.

1. Temporarily add a Django import to the health domain, capture the `lint-imports` failure line, revert.
2. Update `codebase-map.md` areas and `coding-assertions.md` with the gate commands; README with `cp .env.example .env && docker compose up`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `uv run lint-imports` passes on clean code |
| 2 | `pre-commit run --all-files` passes |
| 3 | captured failure shows the broken contract; memory files list the gate commands |
