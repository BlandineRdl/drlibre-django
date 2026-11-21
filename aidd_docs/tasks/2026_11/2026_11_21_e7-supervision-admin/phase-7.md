---
status: pending
---

# Instruction: Suppressions refusées
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/organisation/
│   ├── application/use_cases/delete_clinician_profile.py      ✏️  message « … rendez-vous ou une liste d'attente. »
│   └── application/ports/outbound.py                          ✏️  docstrings des dépendants à jour
└── tests/
    ├── features/organisation/une_suppression_refusee_liste_les_rdv_et_entrees_d_attente_qui_en_dependent.feature ✅
    └── use_cases/organisation/test_une_suppression_refusee_liste_les_rdv_et_entrees_d_attente_qui_en_dependent.py ✅
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | salle, type, profil et utilisateurs ayant des RDV ou des entrées d'attente | prêt | system |
| Edge case | supprimer la salle ayant un RDV | `has_dependents` listant le RDV | system |
| Edge case | supprimer le type ayant un RDV puis une entrée d'attente | `has_dependents` listant chacun | system |
| Edge case | supprimer le profil ayant un RDV | `has_dependents` listant le RDV | system |
| Edge case | supprimer un patient, puis un praticien, ayant des RDV | `has_dependents` listant les RDV, message invitant à désactiver | system |
| Teardown | fakes jetés | baseline | system |

## Tasks to do
### `1)` Scénarios de la Story
> Le comportement existe ; on le prouve puce par puce.

1. Un `.feature` à cinq Scenarios, steps sur fakes réutilisant ceux d'organisation et d'identity.

### `2)` Alignements
> Messages et docstrings exacts.

1. Message du profil, docstrings des ports de dépendants.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | chaque refus liste ce qui utilise encore l'enregistrement |
| 2 | `uv run pytest tests/use_cases/organisation tests/use_cases/identity` vert |
