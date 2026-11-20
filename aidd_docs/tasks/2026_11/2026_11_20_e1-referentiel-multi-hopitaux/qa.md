# Acceptance QA: E1 - Le personnel se connecte et gère le référentiel multi-hôpitaux
- **Verdict**: blocked
- **Source**: `aidd_docs/backlog/epics/le-personnel-se-connecte-et-gere-le-referentiel-multi-hopitaux.md` and its 11 Stories (`aidd_docs/backlog/stories/`, `parent:` that Epic)
- **Candidate**: `feat/e1-referentiel-multi-hopitaux` @ `1e03cb3`, running at `http://localhost:8000` (compose web image rebuilt on that commit)
- **Run**: 2026_11_20

## Out of interface
- « La session dure 12 h pour un admin et 7 jours pour les autres ; elle repart pour une durée pleine quand il en reste moins de la moitié » (time-based, not observable in a take).
- « …dans le même temps de réponse » (timing, not visible).
- « La connexion et la déconnexion sont aussi disponibles par l'API `POST /auth/login` et `POST /auth/logout` » (no browser outcome).
- « Les requêtes d'écriture venant d'une autre origine sont refusées » (needs a forged `Origin`, not a browser journey).
- « Chaque écriture laisse une entrée d'audit sans donnée personnelle ; si l'audit échoue, l'écriture est annulée », and every Story's audit bullet (the audit log screen belongs to the supervision Epic).
- « Un praticien qui a des RDV actifs à venir ne peut pas être désactivé ; le refus liste ces RDV » (appointments do not exist before Epics 2-3).
- « écrans conformes WCAG 2.2 AA, de 375 à 1440 px » (fixed 1280×720 run; covered by the axe e2e tests and the checker's 13-page axe sweep, see `review-2.md`).

## Scenarios
| Scenario | Criteria | Expected | Actual | Verdict | Duration | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Happy path: the admin adds a department to Hôpital Nord, then its deletion is refused | Epic Success Evidence 1; Story départements « Un hôpital qui a des départements ne peut pas être supprimé, et le refus liste ses départements »; Stories « suppression avec confirmation » | Department listed after save; confirmed delete refused, listing « Cardiologie QA (QA-CARD1) » | Listed (`?done=created`); « Suppression refusée : Cet hôpital a encore des départements. » listing its 3 departments, QA one included | pass | 7.25 s | `qa/happy-path.webm` |
| Un praticien qui ouvre la console admin reçoit `forbidden` | Epic Success Evidence 2; Story « Chaque rôle » bullet 2 | Forbidden page | « Accès refusé · Vous n'avez pas accès à cette page avec ce compte. » | pass | 6.42 s | `qa/edge-case-forbidden.webm` |
| Un visiteur sans session est renvoyé vers la connexion | Epic Success Evidence 2; Story « Chaque rôle » bullet 1 | Redirect to sign-in | `/sign-in?next=%2Fconsole%2Fhospitals%2F`, « Se connecter » shown | pass | 5.92 s | `qa/edge-case-anon.webm` |
| Un email inconnu et un mauvais mot de passe donnent le même message | Story connexion bullet 2 (message part) | Same non-empty message twice | « Email ou mot de passe incorrect. » both times | pass | 6.33 s | `qa/edge-case-samemsg.webm` |
| Un admin ne peut pas désactiver son propre compte | Story comptes bullet 3 | Save refused on « Actif » | « Actif : Vous ne pouvez pas désactiver votre propre compte. »; admin still active in DB | pass | 5.00 s | `qa/edge-case-self.webm` |
| Après une connexion avec un mot de passe temporaire, l'utilisateur doit le changer avant d'accéder à son espace | Story mot de passe bullet 2; Story comptes « création avec mot de passe temporaire » | Lands on the change form, and the portal sends back there | `/account/password` both times | pass | 6.75 s | `qa/edge-case-forced.webm` |

Teardowns, each verified to baseline: QA department `QA-CARD1` deleted (count 0); QA user `qa-r1@example.org` and its sessions deleted (count 0); the clinician's failed-attempt count cleared by a successful sign-in; admin active flag unchanged. Audit entries written during the run are kept: the log is append-only by spec §3.1.

## Rejected
- « Après 10 échecs en 15 minutes sur une adresse, la connexion de cette adresse est refusée jusqu'à la fin de la fenêtre » — no teardown inside the run: once locked, a successful sign-in is refused, so the baseline returns only after 15 minutes; covered by `lockout.feature`.
- « Désactiver un utilisateur coupe ses sessions immédiatement » — the trigger (admin) and the outcome (the deactivated user's own session) live in two browser sessions, and one take records one session; covered by `manage_users.feature` and `tests/api/test_console_users.py`.

## Findings
- No product failure. The verdict is `blocked` only because two scenarios were rejected (rule: any rejection → `blocked`); both are covered by the automated suite.
- Note: `tests/e2e/test_admin_journey.py` leaves its data behind (8 « Hôpital E2E … » hospitals with their departments in the demo database); it should tear down or run against a disposable database.
- Note: the browser console logged 2 errors on console pages during preparation; not investigated.
