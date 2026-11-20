# Review: E2 - Les praticiens publient leurs disponibilités et les créneaux libres en découlent
## Round 1
- Diff: `main...0c2bb7a`
- Uncommitted changes: oui (`CLAUDE.md`, hors périmètre, ignoré)
- Axes: code, functional, relevancy
- Verdict: changes-requested, parce qu'un changement de fuseau d'hôpital ou d'hôpital de département laisse la table `scheduling_slot` périmée (finding majeur)

### Criteria
- [x] §5.1 étapes 1–4 (pas, durée ≤ fin de plage, bornes, passé, absences, buffer du type demandé, dédoublonnage trié) — `scheduling/domain/slot_engine.py:22-47`, `infrastructure/slot_queries.py:20-30`
- [x] Plafond de 31 jours en `invalid_input` — `application/use_cases/find_free_slots.py:24`
- [x] Union des praticiens actifs seulement — `infrastructure/directory.py:28-31`, filtre à la lecture
- [x] Heure locale stable au changement d'heure — `slot_engine.py:46-47`, `tests/integration/test_slot_refresh_postgres.py:123`
- [x] Rafraîchissement dans l'unité de travail de chaque écriture plage/absence/type/profil — `clinician_writes.py:62-74`, `records.py:64-66`, `edit_clinician_profile.py:50-51`
- [x] Audit sans donnée personnelle (jour, champs changés, motif exclu) — `save_availability_rule.py:56-58`, `record_time_off.py:43-49`
- [x] Identité par la session, propriété vérifiée — `clinician_writes.py:38-49`
- [x] Horizon de 90 jours, job quotidien — `refresh_slots.py:68-73`, `config/celery.py`
- [x] Chaque puce d'Acceptance des 7 Stories est un nom de scénario
- [ ] Rafraîchissement sur toute écriture qui change les créneaux (Decision du plan) — fuseau d'hôpital et rattachement département→hôpital absents
- Unverified at runtime: parcours e2e et axe-core 375/1440 px — `uv run pytest -m e2e` non lancé sur ce head

### Assumptions
- `ActiveAppointments` ne renvoie que des RDV actifs — vrai par contrat, mais la règle « actif » vit dans le fake (finding), `tests/fakes/scheduling.py:23,73`
- Le fuseau d'un praticien ne change qu'à l'édition de son profil — faux, finding, `organisation/application/use_cases/save_hospital.py:20-27`
- Le job tourne une fois par jour à 00:15 `CELERY_TIMEZONE` — tient pour Europe/Paris, limite pour d'autres fuseaux
- Gates : 407 tests verts, `lint-imports` 7 contrats gardés, Ruff, Pyrefly 0 erreur, `makemigrations --check` propre

### Findings
- `src/drlibre/organisation/application/use_cases/save_hospital.py:20-27` et `save_department.py:28-35` : changer le `time_zone` d'un hôpital ou le `hospital_id` d'un département ne rafraîchit pas les créneaux ; la table garde les instants UTC de l'ancien fuseau (décalés de l'écart horaire) jusqu'au job de 00:15, alors que le plan exige « shown = bookable » dans la même transaction, preuve `scheduling/application/use_cases/refresh_slots.py:44` (fuseau lu à la reconstruction seulement) → passer `written=` à `RecordWrites.save` dans les deux use cases, appeler `SlotRefresh.refresh` sur les profils des départements concernés (hôpital : tous ses départements), plus un scénario par cas — 🟡 major (bloquant au sens de l'appelant : bug de correction)
- `tests/fakes/scheduling.py:23,73` : le fake `InMemoryActiveAppointments` porte la règle métier « CANCELLED/NO_SHOW ne sont pas actifs » ; les scénarios « Un RDV CANCELLED ou NO_SHOW ne retire aucun créneau » et « un RDV qui devient actif ou cesse de l'être » (`les_absences_et_les_rdv_actifs_retirent_des_creneaux.feature:22,32`) ne testent que le fake, aucun code de production, contre `aidd_docs/memory/testing.md` (fakes sans règle métier) → faire renvoyer statut + période par le port et filtrer dans le domaine (`is_active` partagé), le fake restant un simple stockage — 🟡 major (non bloquant)
- `tests/features/scheduling/les_plages_du_praticien_donnent_ses_creneaux_libres.feature:11` : le scénario nommé « …sans session, il répond unauthenticated (type, praticien et période) » ne vérifie pas `unauthenticated` (seul `tests/api/test_slots_endpoint.py:23` le fait), contre la règle 5-acceptance-test-names « chaque scénario teste exactement ce que son nom affirme » → ajouter un scénario « (sans session) » ou renommer le qualificatif — 🟢 minor
- `src/drlibre/scheduling/application/use_cases/save_availability_rule.py:55,74` et `record_time_off.py:41` : contrôles de chevauchement et de doublon hors de l'unité de travail, sans contrainte en base ; deux POST concurrents peuvent enregistrer deux plages qui se chevauchent → déplacer le contrôle dans `with uow` avec `select_for_update` sur le profil (ou verrou consultatif) — 🟢 minor
- `src/drlibre/scheduling/application/use_cases/find_free_slots.py:24` : le plafond compare une durée absolue ; 31 jours locaux traversant le passage à l'heure d'hiver font 31 j + 1 h et sont refusés → comparer les dates locales du fuseau de l'hôpital, ou tolérer l'écart DST — 🟢 minor
- `src/drlibre/interfaces/web/presenters/availability.py:192-198,227-229` : `?week=0001-01-01` ou `9999-12-31` lève `OverflowError` (500) au calcul des liens, contre §4 (valeur d'adresse inutilisable → défaut) → retomber sur `today` si `day` est hors `date.min + 7j … date.max - 7j` — 🟢 minor
- `src/drlibre/interfaces/web/views/workspace_availability.py:55-61,111` : `q.room(o.id)` pour chaque salle de tous les hôpitaux et pour chaque plage (N+1) → une requête des salles actives du département — 🟢 minor
- `src/drlibre/interfaces/web/presenters/availability.py:13` duplique `WEEKDAYS` de `scheduling/domain/availability_rule.py:11` ; `workspace_availability.py:39-52` (`_me`, `_owned`) redouble `ClinicianWrites.caller/owned` → importer le tuple du port, garder les pré-contrôles web minimaux — 🟢 minor

### Limits
- Horizon hors Europe/Paris : job à 00:15 Paris, un hôpital en America/New_York n'a pendant ~18 h que J+89 — un scénario multi-fuseau le trancherait
- Étapes en UTC sur une plage qui chevauche le changement d'heure nocturne (01:00–04:00) : débuts décalés de la grille locale ; hors périmètre réaliste, non spécifié
- Absences passées chargées entièrement à chaque rafraîchissement (`repositories.py:83-84`) : coût croissant dans le temps, à borner sur la fenêtre
- Parcours e2e et WCAG à 375/1440 px non exécutés sur ce head ; templates lus : captions, `scope`, `aria-label`, région défilable focusable, fuseau nommé
