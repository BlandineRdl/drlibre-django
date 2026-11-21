---
paths:
  - "src/drlibre/**/application/**/*.py"
  - "src/drlibre/**/infrastructure/**/*.py"
  - "tests/integration/**/*.py"
---
# Counters under lock
- Run any read-modify-write of a counter, attempt count or limit under `select_for_update`.
- Take the lock through a port, inside the unit of work of the write.
- Re-read the record after taking the locks and decide on that copy; a read taken before them is stale.
- Prove it with a two-transaction PostgreSQL test, per the concurrent-write row of `aidd_docs/memory/testing.md`.
- The test must fail with the lock removed.

<!-- aidd_rule_output:path=.claude/rules/07-quality/7-counters-under-lock.md sha256=a3d4b2264a97396932fbb5f6b364ddc9d1a87fd03cf927187e60ad1a4c0f710b -->
