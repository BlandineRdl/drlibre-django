<!-- aidd_rule:{"version":1,"category":"07-quality","slug":"7-counters-under-lock","description":"Counters and limits are read-modify-written under a row lock","paths":["src/drlibre/**/application/**/*.py","src/drlibre/**/infrastructure/**/*.py","tests/integration/**/*.py"],"targets":["claude"]} -->
# Counters under lock
- Run any read-modify-write of a counter, attempt count or limit under `select_for_update`.
- Take the lock through a port, inside the unit of work of the write.
- Re-read the record after taking the locks and decide on that copy; a read taken before them is stale.
- Prove it with a two-transaction PostgreSQL test, per the concurrent-write row of `aidd_docs/memory/testing.md`.
- The test must fail with the lock removed.
