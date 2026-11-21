---
status: done
---

# Instruction: Écrans tableau de bord, journal et réglages
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/interfaces/web/
│   ├── urls.py                                                 ✏️  `console/audit/`, `console/settings/`, `console/settings/reminders`
│   ├── views/areas.py                                          ✏️  `/console/` devient le tableau de bord
│   ├── views/console_audit.py                                  ✅  journal filtré
│   ├── views/console_settings.py                               ✅  constantes, bouton rappels
│   ├── presenters/console.py                                   ✏️  « Journal d'audit », « Réglages » dans `_SECTIONS`, « Accueil » → « Tableau de bord »
│   ├── presenters/dashboard.py                                 ✅  tuiles, « n/a », barres, top 5
│   ├── presenters/console_audit.py                             ✅  filtres, lignes, fuseau
│   ├── templates/areas/home.html                               ✏️  tableau de bord
│   └── templates/console/{audit.html,settings.html}            ✅
├── static/drlibre.css                                          ✏️  barres de l'histogramme
└── tests/
    ├── presenters/test_dashboard_presenters.py                  ✅  « n/a », pourcentages, barres
    ├── presenters/test_console_audit_presenters.py              ✅
    └── api/test_console_supervision_pages.py                    ✅  tableau de bord, journal, réglages, bouton
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | admin connecté, activité sur deux hôpitaux | prêt | browser |
| Happy path | `/console/?range=30` | tuiles §13, histogramme 30 jours, top 5 | browser |
| Edge case | aucune activité | « n/a » sur chaque ratio | browser |
| Happy path | `/console/audit/?actor=…&entity_type=appointment&from=…` | entrées filtrées, plus récentes d'abord, correlation id | browser |
| Edge case | filtre inutilisable | défaut | browser |
| Happy path | Réglages → « Lancer les rappels » | « N rappels envoyés » ; second clic « 0 rappel envoyé » | browser |
| Edge case | praticien sur ces pages | 403 | browser |
| Teardown | base vidée | baseline | browser |

## Wireframe
```txt
┌──────────────────────────────────────────────────┐
│ (1) Nav console                                   │
├──────────────────────────────────────────────────┤
│ (2) Tableau de bord  [Aujourd'hui][7 jours][30 j] │
│ (3) Tuiles : RDV · Annulations · Utilisation ·    │
│     Taux d'absence · Part en ligne · Attente      │
│ (4) RDV par jour : tableau jour │ ████ 12         │
│ (5) Praticiens les plus chargés : 1…5 nom · n     │
├──────────────────────────────────────────────────┤
│ (6) Journal d'audit — heures en Europe/Paris      │
│     <search> Acteur (email) [ ] Entité [▾]        │
│     Du [ ] Au [ ] [Filtrer]                       │
│     Heure · Acteur · Action · Entité · Corr. id   │
│     [◀ Précédent] [Suivant ▶]                     │
├──────────────────────────────────────────────────┤
│ (7) Réglages : délai 120 min · annulation 24 h ·  │
│     3 réservations en ligne · [Lancer les rappels]│
└──────────────────────────────────────────────────┘
```
1. Nav : sections console.
2. Choix de période en liens, courante marquée `aria-current`.
3. Tuiles `dl.tiles` ; ratio nul → « n/a ».
4. Tableau de données, barre CSS proportionnelle, nombre en texte.
5. Liste ordonnée, ou « Aucun RDV sur la période ».
6. Journal en lecture seule, tableau défilant, pagination avec filtres.
7. Constantes en lecture seule, bouton POST avec notice.

## Tasks to do
### `1)` Tableau de bord
> `ViewDashboard`, période en lien.

1. Presenter : tuiles, pourcentages, barres en % du maximum, top 5.

### `2)` Journal d'audit
> `AuditQueries.page`, acteur résolu par email.

1. Filtres, `entity_types` en liste fermée, heures en `settings.TIME_ZONE`.

### `3)` Réglages
> Constantes et `RunReminders`.

1. POST → redirection `?done=reminders&count=N`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | « n/a » quand le dénominateur est nul ; barres et top 5 suivent la période |
| 2 | aucun formulaire ni bouton de modification ; correlation id visible |
| 3 | le second lancement n'envoie rien |
| all | `uv run pytest tests/presenters tests/api` vert |
