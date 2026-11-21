---
paths:
  - "src/drlibre/**/*.py"
---
# Domain errors
- Signal an expected failure by raising `DomainError(ErrorCode.<CODE>, message, details)`; never raise bare exceptions for business outcomes.
- Use only `ErrorCode` members from spec 4; add a code to the spec, the enum and `_HTTP_STATUS` together.
- Derive HTTP statuses only from `ErrorCode.http_status`; domain and application code never mention HTTP.
- Let the Ninja handler serialize `{code, message, details}`; API routers do not catch `DomainError` themselves.
- Web views catch only the refusals their page re-renders: `invalid_input` on a form, `has_dependents` and `forbidden` on a form or delete confirmation, and booking and portal pages also `rule_violation`, `invalid_transition`, `conflict`, `no_clinician_available` and `no_room_available` inline; `DomainErrorPagesMiddleware` turns every other code into its error page.
- Keep `details` to ids, field names and resource lists; never personal data.

<!-- aidd_rule_output:path=.claude/rules/06-design-patterns/6-domain-errors.md sha256=272c768ed4b7b8d4064d396e7d714210c20f8ed42b4ce8bcbcf95f68cd5127ae -->
