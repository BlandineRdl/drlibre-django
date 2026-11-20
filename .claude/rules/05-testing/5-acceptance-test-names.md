---
paths:
  - "tests/**/*.feature"
  - "tests/**/*.py"
---
# Acceptance test names
## Gherkin
- One `.feature` file per Story: `Feature:` is the Story title as written in `aidd_docs/backlog/stories/<slug>.md`, followed by its En tant que / Je veux / Afin de lines.
- Each `Scenario:` name is one Acceptance bullet of that Story in its own French wording; several scenarios for one bullet keep that wording and add a short qualifier in parentheses.
- A scenario proving a spec rule outside the Story bullets is named `Règle §<n> : <the rule in French>`.
- Every Acceptance bullet appears in at least one scenario name, and each scenario tests exactly what its name claims.
- A `Scenario Outline` name interpolates only a `case` column written in user words; roles, ids, codes, URLs and enum values stay in steps and `Examples`.
- Never use technical labels in names, such as `happy path`, `edge case` or `test_repo_save`.

## Other tests
- Contract, integration, presenter and API test function names state the observable business behaviour; the docstring cites the Story or spec rule it proves when one applies.

<!-- aidd_rule_output:path=.claude/rules/05-testing/5-acceptance-test-names.md sha256=1026f8c6f424c93ee256aa5c70927fe169e5364245929c5336b7059ac18ae4ea -->
