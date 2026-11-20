---
objective: "Un praticien gère ses plages hebdomadaires et ses absences, et `GET /slots` renvoie, depuis la table `slot` tenue à jour dans la même transaction, les créneaux libres justes de §5.1, l'admin voyant résumé et calendrier en lecture seule."
status: implemented
---

# Plan: E2 - Les praticiens publient leurs disponibilités et les créneaux libres en découlent
## Overview
| Field | Value |
| --- | --- |
| **Goal** | Nouveau contexte `scheduling` : plages, absences, moteur de créneaux, table `slot` précalculée, `GET /slots`, écrans praticien et admin |
| **Source** | GitHub issue #5, `aidd_docs/backlog/epics/les-praticiens-publient-leurs-disponibilites-et-les-creneaux-libres-en-decoulent.md` et ses 7 Stories (`parent:` cet Epic) ; spec §3.1, §4, §5.1, §9, §10, §14, §16 |

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | Moteur de créneaux et lecture des créneaux sur fakes | [`phase-1.md`](./phase-1.md) | none |
| 2 | Plages et absences : écriture, audit, persistance | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Table `slot` PostgreSQL, rafraîchissement transactionnel, horizon quotidien | [`phase-3.md`](./phase-3.md) | 2 |
| 4 | `GET /slots`, écrans praticien, résumé et calendrier admin | [`phase-4.md`](./phase-4.md) | 3 |
| 5 | Seed, parcours end-to-end, documentation | [`phase-5.md`](./phase-5.md) | 4 |

## Resources
| Source | Verified |
| --- | --- |
| https://docs.python.org/3/library/zoneinfo.html | `datetime.combine(day, time, tzinfo=ZoneInfo(tz))` gives the local wall time; `fold` and the gap at spring-forward are handled by converting to UTC; executor confirms with a Hypothesis property over the March and October 2026 Europe/Paris changes |
| https://hypothesis.readthedocs.io/en/latest/ | already declared (`pyproject.toml` line 26); used for `SlotEngine` behaviour properties |
| https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html | `beat_schedule` entry with `crontab(hour=..., minute=...)` from `celery.schedules`; `config/celery.py` already holds the heartbeat entry |
| https://docs.djangoproject.com/en/6.1/ref/models/indexes/ | composite `models.Index(fields=[...])` on the slot table for `(appointment_type, start)` and `(clinician, appointment_type, start)` |

## Decisions
| Decision | Why |
| --- | --- |
| New bounded context `drlibre.scheduling` (domain, application, infrastructure), added to the import-linter layers and to a forbidden contract keeping its core free of `identity` and `organisation` | INSTALL.md lists `scheduling`; availability, time off and slots are its own language; other contexts reached only through ports |
| A clinician is identified by its clinician profile id in rules, time off, slots and `GET /slots` (`clinician=`) ; the web resolves the session user to its profile | the profile carries department and hospital, so its time zone; public "provider" pages (E3) will use the same id |
| Table `scheduling_slot(clinician, appointment_type, start, end)` holds free slots per clinician and type, from today to today + 90 days; a clinician's rows are rebuilt by the pure `SlotEngine` inside the unit of work of every write that changes them | precomputed table owned by E2 (shadow report); "shown = bookable" needs the same transaction |
| Refresh triggers: rule and time-off writes (E2), and through an organisation outbound port `SlotRefresh` the appointment type save and the clinician profile attach, edit, delete; holds and appointments (E3+) will call the same inbound port | duration, buffer and department change the slots; contexts meet only through ports |
| `starts in the past` and `inactive clinician` are filtered at read time, never left to the job; the daily job only rebuilds the horizon | mirrors the hold-expiry gotcha: correctness never depends on a scheduled job |
| Active appointments are read through an outbound port `ActiveAppointments` with the null adapter `NoAppointmentsYet` (empty); BDD scenarios inject them through its fake | Epic assumption: calcul vérifié contre des RDV actifs injectés en test |
| Overlapping rule and duplicate time off are refused as `invalid_input` on the field, with a message naming the clash | web views re-render only `invalid_input`; spec §4 reserves `conflict` for clinician/patient/room booking overlaps |
| Editing a rule keeps its valid-from date; a modified or deleted rule, like time off, never touches existing appointments | spec §9 says "a new rule is valid from today"; no appointment exists before E3 |
| `GET /slots` answers `not_found` for an unknown or inactive type, or a clinician unknown, inactive or outside the type's department; slots beyond the 90-day horizon are simply absent | answers the E2 open questions; no extra error code |
| Admin calendar: week grid 07:00–19:00 in 30-minute rows showing rule blocks and time off, with previous / next / this week links; summary: weekday and HH:MM–HH:MM ranges per clinician | answers the open question; mirrors the clinician calendar of §9 without appointments yet |
