---
objective: "Un admin global suit les indicateurs de §13 sur un tableau de bord, liste, exporte et pilote n'importe quel RDV, réserve pour un patient, consulte le journal d'audit et lance les rappels, chaque Story de l'Epic E7 prouvée par ses scénarios."
status: pending
---

# Plan: E7 - L'admin supervise l'activité de tous les hôpitaux
Source: GitHub issue #10, `aidd_docs/backlog/epics/l-admin-supervise-l-activite-de-tous-les-hopitaux.md` et ses 10 Stories (commentaire de l'issue) ; spec §4, §5.2–§5.8, §10, §13, §14, §16 ; questions ouvertes E7 de `aidd_docs/backlog/open-questions.md`

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | L'admin agit sur n'importe quel RDV | [`phase-1.md`](./phase-1.md) | none |
| 2 | Lectures admin : RDV, export, patients, audit, rappels | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Contexte reporting : indicateurs, jours, praticiens chargés | [`phase-3.md`](./phase-3.md) | none |
| 4 | API admin | [`phase-4.md`](./phase-4.md) | 1, 2 |
| 5 | Écrans RDV de la console | [`phase-5.md`](./phase-5.md) | 1, 2 |
| 6 | Écrans tableau de bord, journal et réglages | [`phase-6.md`](./phase-6.md) | 2, 3 |
| 7 | Suppressions refusées | [`phase-7.md`](./phase-7.md) | none |
| 8 | Seed, parcours end-to-end, documentation, gates | [`phase-8.md`](./phase-8.md) | 4, 5, 6, 7 |

## External sources
| URL | What it settled |
| --- | --- |
| https://owasp.org/www-community/attacks/CSV_Injection | une cellule qui commence par `=`, `+`, `-`, `@` est préfixée d'une apostrophe (§13) ; tabulation et retour chariot en tête traités de même |
| https://docs.python.org/3/library/csv.html | `csv.writer` cite les champs ; `StreamingHttpResponse` + écrivain pseudo-buffer pour tout l'ensemble filtré |
| https://www.postgresql.org/docs/current/functions-datetime.html#FUNCTIONS-DATETIME-ZONECONVERT | `start AT TIME ZONE <fuseau>` donne le jour local ; même conversion que `search/infrastructure/sql_queries.py:60-66` (`s.start AT TIME ZONE p.time_zone`), ici `h.time_zone` de l'hôpital du département du praticien |
| https://www.w3.org/WAI/WCAG22/Understanding/non-text-content.html | l'histogramme est un tableau de données dont chaque barre porte aussi son nombre en texte |

## Impact
| Category | Verdict and evidence | Handled in |
| --- | --- | --- |
| Runtime | none new: PostgreSQL, Redis, Celery, Mailpit déjà là ; `POST /jobs/reminders` et le bouton appellent `SendRemindersUseCase` en synchrone (`booking/application/use_cases/send_reminders.py`), le beat `send-appointment-reminders` (`config/celery.py:17`) reste ; migration `booking.0005` (index `start`) jouée par l'entrypoint | 2, 3, 8 |
| Regression | medium : les gardes `own_appointment_of` (`own_clinician_appointment.py:46`), `locked_clinician_appointment` (`:30`) et `clinician_profile` (`:10`) refusent l'admin dans cancel, reschedule, `StatusChange`, `BookForPatient`, `ListAppointmentsAsCaller` ; `reschedule_violations(for_patient=profile_id is None)` (`reschedule_appointment.py:72`) traiterait l'admin en patient ; `tests/api/test_appointment_actions.py:87` épingle le `forbidden` admin (« l'admin attend E7 ») et doit être réécrit ; `/console/` placeholder (`views/areas.py console_home`). Couvert par `tests/features/booking/*`, `tests/api/test_appointment_actions.py`, `test_clinician_appointment_actions.py`, `test_appointments_list.py`, relancés à chaque phase ; pas de phase filet | 1, 4, 5, 6 |
| Architecture | booking gagne une portée d'acteur (`ActorScope` : patient, praticien, admin via `Staff.is_admin` déjà présent `ports/outbound.py:196`), une lecture SQL `AdminAppointments` et `ExportAppointments` ; audit gagne `AuditQueries.page` et `entity_types` ; identity gagne `PatientLookup.active_patients` ; nouveau contexte `drlibre.reporting` lecture seule SQL comme `search` (domaine pur pour les minutes disponibles), ajouté aux contrats import-linter (`pyproject.toml:105`, contrat forbidden calqué sur Search `:137-149`) | 1, 2, 3 |
| Documentation | `architecture.md` (portée admin, reporting, export, audit lu), `codebase-map.md` (reporting, écrans console), `open-questions.md` (réponses E7 ci-dessous) ; spec et Stories inchangées | 8 |

## Rules
| Rule | Why it applies |
| --- | --- |
| `aidd_docs/rules/00-architecture/0-context-boundaries.md`, `0-ports-and-use-cases.md` | reporting lit en SQL sans importer d'autre contexte ; un `execute()` par use case |
| `aidd_docs/rules/00-architecture/0-interfaces-no-business-rule.md` | actions permises, ratios et « n/a » calculés hors templates |
| `aidd_docs/rules/02-programming-languages/2-python-value-objects.md` | lignes, filtres et indicateurs en dataclasses gelées |
| `aidd_docs/rules/05-testing/5-acceptance-test-names.md`, mémoire `test-names-mirror-acceptance` | un `.feature` par Story, Scenarios = puces d'acceptance en français |
| `aidd_docs/rules/05-testing/5-fakes-and-contracts.md` | chaque nouveau fake (`AdminAppointments`, `AuditQueries.page`, `PatientLookup`) a son contrat |
| `aidd_docs/rules/06-design-patterns/6-domain-errors.md` | `forbidden`, `invalid_transition`, `invalid_input`, `conflict`, `no_room_available` via `DomainError`, rendus en ligne |
| `aidd_docs/rules/07-quality/7-counters-under-lock.md` | les écritures admin relisent le RDV sous les verrous praticien puis patient |
| Chaque écriture auditée dans sa transaction, métadonnées sans donnée personnelle | export `{count}`, actions admin comme celles du praticien |
| Ordre des verrous email, praticien, patient, salles (architecture.md) | les actions admin le gardent |
| Search filters and sorts testés en pytest-bdd sur PostgreSQL (`testing.md`) | les règles de liste, d'export et d'indicateurs vivent dans le SQL |
| WCAG 2.2 AA de 375 à 1440 px ; presenters construisent les ViewModels | §16 |
| Commentaires d'une ligne | CLAUDE.md utilisateur |

## Decisions
| Decision | Why |
| --- | --- |
| Portée d'acteur `actor_scope(directory, staff, actor_id) -> ActorScope(kind, profile_id)` : profil → praticien, `Staff.is_admin` → admin, sinon patient ; `scoped_appointment(scope, appointments, id)` : admin lit tout RDV (`not_found` si absent), praticien et patient gardent leurs gardes | une seule garde partagée par cancel, reschedule, statuts, notes refusées à l'admin |
| L'admin suit les règles du personnel : pas de 24 h, `reschedule_violations(for_patient=False)`, transitions de `clinician_actions` | Story annule ; §5.3 « staff bound only by availability and conflicts » |
| Les notes cliniques restent au praticien seul ; l'admin reçoit `forbidden` | §3.1, Epic ne les cite pas |
| `BookForPatient` pour l'admin : `clinician_id` obligatoire (`invalid_input` sur `clinician`), patient actif (`refuse_non_patient`), type de n'importe quel département actif, salle nommée active du département du type (`not_found`) puis libre (`conflict`) ; `for_patient=False`, source `STAFF` | Story réserve, §14 « exige un praticien pour l'admin » ; question ouverte salle |
| « Plus récents d'abord » = `start` décroissant puis `id` ; colonnes : début (fuseau de l'hôpital, nommé), patient, praticien, département, type, statut, source, salle | question ouverte ; `AppointmentRecord` n'a pas de `created_at` |
| Filtres liste et export : `from`, `to` (dates locales incluses, jour local de l'hôpital du RDV), `department`, `clinician`, `status`, `source` ; valeur inutilisable → défaut (aucun filtre) ; page via `PageRequest.from_query` | Story liste ; même parse que la liste d'attente |
| Index `appointment_start` sur `start` (migration `booking.0005`) | aucune colonne `start` seule indexée ; liste, export et tableau de bord balaient tous les hôpitaux |
| Export : `ExportAppointments.execute(actor_id, filter) -> tuple[ExportRow, ...]` admin seul, une entrée d'audit `booking.appointments_exported` `{count}` ; l'interface écrit le CSV, `csv_cell` préfixe `'` devant `= + - @ \t \r` | §13 ; l'encodage est un détail d'interface, la règle est testée au presenter |
| Choix du patient : identity `PatientLookup.active_patients(text) -> tuple[PatientMatch, ...]` (patients actifs, `ILIKE` sur nom ou email, 20 max, nom puis email) | Story réserve ; aucune recherche de patients actifs aujourd'hui |
| Assistant de réservation admin : patient → type (tous les types actifs) → praticien du département du type → semaine de créneaux `FindFreeWeek(for_patient=False)` → salle facultative → confirmation ; pas de « premier disponible » | Story réserve |
| Les actions admin (arrivé, terminé, absent, annuler, déplacer) partent de la fiche `/console/appointments/<id>`, liée depuis chaque ligne de la liste | question ouverte « d'où » |
| Contexte `drlibre.reporting` lecture seule : `DashboardQueries.dashboard(range)` en SQL (comptes, minutes actives, jours, top 5, liste d'attente) + domaine pur `available_minutes(rules, time_offs, days, zone)` (plages moins absences, clippées aux jours) testé par Hypothesis | §13 ; `SlotEngine` compte des créneaux, pas des minutes |
| Période `?range=today|7|30`, défaut `7` ; jours = aujourd'hui local de chaque hôpital et les n−1 précédents ; minutes disponibles dans le fuseau de l'hôpital de chaque praticien ; praticien actif = utilisateur actif de rôle `CLINICIAN` | question ouverte ; Epic assumption fuseau |
| Ratios : utilisation, absences, part en ligne en `Ratio(num, den)` ; dénominateur nul → « n/a » ; pourcentage arrondi à l'entier | §13 |
| Top 5 : nombre de RDV non annulés décroissant puis nom du praticien ; moins de 5 praticiens ayant au moins un RDV → seulement ceux-là, aucun → « Aucun RDV sur la période » | question ouverte égalités |
| Journal d'audit : `AuditQueries.page(AuditFilter(actor_id, entity_type, from, to), PageRequest)` plus récent d'abord avec total ; filtre acteur par email résolu par identity `user_by_email` (inconnu → aucune entrée, email mal formé → défaut) ; types d'entité en liste fermée `AuditQueries.entity_types()` ; heures dans `settings.TIME_ZONE`, nommé sur la page ; acteur affiché par son email, vide sinon | question ouverte fuseau ; les entrées n'ont pas d'hôpital |
| Réglages : constantes de `shared_kernel/booking_policy.py` affichées ; bouton → `RunReminders.execute(actor_id) -> int` (admin seul, `forbidden` sinon) qui appelle `SendReminders` ; notice « N rappels envoyés » | question ouverte bouton ; une seule exécution, l'index unique garde l'unicité |
| `GET /appointments` admin : filtres de la liste, `page`, réponse `{items, total, page}` sans notes ni texte libre au-delà du motif ; `POST /jobs/reminders` → `{count}` | §14 « limited to what the caller may see » |
| Suppressions : comportement déjà là (`any_for_user`, `dependents_of_room`, types, profils) ; on ajoute les scénarios manquants et on aligne le message du profil (« Ce praticien a des rendez-vous ou une liste d'attente. ») | rapport d'exploration ; Story suppression |
| Journal en lecture seule : garanti par les triggers `audit.0002` (UPDATE, DELETE, TRUNCATE refusés) ; aucune écriture exposée ; le test append-only existant prouve la puce | Story journal ; architecture.md |
| Seed démo : RDV passés insérés par ORM `bulk_create` comme `_load_appointments` (`scripts/seed.py:367`), ids `uuid5` fixes pour l'idempotence (`ignore_conflicts`), statuts et sources variés ; sans audit (données de démo, comme la seed de charge) ; `RefreshSlots` des praticiens touchés ensuite ; deux entrées d'attente par `JoinWaitlist` | les use cases refusent un début passé (`outside_availability`) |
| Pas de run Locust : la recherche et la réservation anonyme ne changent pas ; les lectures admin s'appuient sur le nouvel index `start` | p95 prouvé par E3 |
