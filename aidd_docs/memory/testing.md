# Testing
## Layers
| Change | Test |
| --- | --- |
| A use case or business behaviour | Gherkin scenario run with pytest-bdd on in-memory fakes |
| A domain rule with many edge cases, such as slots or round robin | Behaviour-level test with Hypothesis properties, never its internal functions |
| A presenter or ViewModel | Unit test of the ViewModel the template renders |
| A port or adapter | Contract suite run against the fake and the real adapter |
| An ORM, SQL, mail or Redis adapter | Integration test on PostgreSQL, Mailpit or Redis |
| The FHIR API | FHIR R4 contract test |
| A user journey | A few Playwright end-to-end tests |
| Search or booking performance | Locust load scenario on the demo seed |

## Conventions
- Test behaviour, not functions: a refactoring that keeps behaviour breaks no test.
- No mocks on owned ports; in-memory fakes implement them, with trivial behaviour and no business rule.
- Contract tests keep each fake identical to its real adapter.
- Time comes from the `Clock` port; test data comes from hand-written builders.
- Unowned services are tested through their real adapter in integration.
- Mutation testing with mutmut measures test quality instead of coverage.
