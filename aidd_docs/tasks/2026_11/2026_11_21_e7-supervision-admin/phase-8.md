---
status: pending
---

# Instruction: Seed, parcours end-to-end, documentation, gates
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── scripts/seed.py                                             ✏️  RDV passés dans tous les statuts et sources, entrées d'attente
├── tests/e2e/test_admin_supervises_activity.py                 ✅  tableau de bord, liste, export, action, réservation, journal, réglages, axe 375/1440
├── aidd_docs/memory/architecture.md                            ✏️  portée admin, reporting, export, journal
├── aidd_docs/memory/codebase-map.md                            ✏️  `reporting/`, écrans console
└── aidd_docs/backlog/open-questions.md                         ✏️  réponses E7
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d --build`, seed démo | RDV de tous statuts | system |
| Happy path | admin : tableau de bord, filtre, export, annule, réserve un type non réservable en ligne, journal, rappels | chaque écran répond, `STAFF` visible, entrée d'audit d'export | browser |
| Edge case | axe-core à 375 et 1440 px sur chaque écran | aucune violation | browser |
| Teardown | données du run nettoyées, limites de débit remises | baseline | browser |

## Tasks to do
### `1)` Seed
> Indicateurs non nuls sur la démo.

1. RDV des 7 jours passés `COMPLETED`, `CANCELLED`, `NO_SHOW` et sources `ONLINE`, `ROUND_ROBIN`, `STAFF` par `bulk_create` (ids `uuid5`, `ignore_conflicts`), puis `RefreshSlots` ; deux entrées d'attente par `JoinWaitlist` si absentes.

### `2)` Parcours
> Un parcours Playwright admin.

1. Helpers de `tests/e2e/pages.py`.

### `3)` Documentation
> Mémoire à jour.

1. `architecture.md`, `codebase-map.md`, `open-questions.md` d'après les Decisions du plan.

### `4)` Gates
> Contributor checks.

1. `uv run ruff check .`, `uv run ruff format --check .`, `uv run pre-commit run --all-files`, `uv run lint-imports`, `uv run pytest`, `uv run pytest -m e2e`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | seed relancée deux fois sans doublon |
| 2 | parcours vert, axe sans violation |
| 3 | les questions E7 portent leur réponse |
| 4 | toutes les gates vertes |
