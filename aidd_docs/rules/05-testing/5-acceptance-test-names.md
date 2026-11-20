<!-- aidd_rule:{"version":1,"category":"05-testing","slug":"5-acceptance-test-names","description":"Test names restate the Story acceptance criteria they prove","paths":["tests/**/*.feature","tests/**/*.py"],"targets":["claude"]} -->
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
