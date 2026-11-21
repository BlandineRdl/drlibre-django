---
status: done
---

# Instruction: Job d'expiration planifié
## Architecture projection
> Tree of the final files from the project root, each folder ending in `/`. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/drlibre/booking/
│   ├── application/ports/inbound.py                             ✏️  `ExpireWaitlist`
│   └── application/use_cases/expire_waitlist.py                 ✅
├── src/drlibre/interfaces/jobs/tasks.py                         ✏️  `drlibre.expire_waitlist`
├── config/celery.py                                             ✏️  `expire-waitlist` every 60.0 s
├── src/drlibre/bootstrap/container.py                           ✏️  `expire_waitlist`
└── tests/
    ├── features/booking/{une_entree_dont_la_fenetre_est_passee_expire,une_offre_non_acceptee_a_temps_libere_l_entree}.feature ✅
    ├── use_cases/booking/{test_une_entree_dont_la_fenetre_est_passee_expire.py,test_une_offre_non_acceptee_a_temps_libere_l_entree.py} ✅
    └── integration/test_waitlist_expiry_postgres.py             ✅  task on PostgreSQL; beat entry present
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | fake world: `WAITING` past and future windows, `OFFERED` whose slot started (window open, window passed), `OFFERED` still future | ready | system |
| Happy path | run the job | past `WAITING` → `EXPIRED`; started `OFFERED` → `WAITING` or `EXPIRED`; future ones unchanged; one audit entry each, actor empty | system |
| Edge case | `EXPIRED` entry at the next cancel; lapsed `WAITING` entry at the next cancel | no offer; offer received | system |
| Edge case | second run | changes nothing, writes no audit | system |
| Teardown | fakes discarded | baseline | system |

## Tasks to do
### `1)` Use case
> One unit of work over locked rows.

1. `ExpireWaitlistUseCase.execute() -> int`: `expiring_locked(now)`; `expired()` or `back_to_waiting()` then `expired()` when `latest <= now`; save; audit `booking.waitlist_expired` or `booking.waitlist_offer_lapsed` with the status.

### `2)` Schedule
> Runs without an admin.

1. Celery task in `bound_contextvars(correlation_id=...)` logging the count; beat entry `expire-waitlist` every 60.0 s.

### `3)` Story scenarios
> Stories « expire », « libère l'entrée ».

1. One scenario per acceptance bullet.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | idempotent; audit per changed entry only |
| 2 | `app.conf.beat_schedule` holds the entry; the task runs the use case |
| 3 | each acceptance bullet maps to a scenario name |
