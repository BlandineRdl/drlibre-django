---
paths:
  - "src/drlibre/**/*.py"
---
# Domain errors
- Signal an expected failure by raising `DomainError(ErrorCode.<CODE>, message, details)`; never raise bare exceptions for business outcomes.
- Use only `ErrorCode` members from spec 4; add a code to the spec, the enum and `_HTTP_STATUS` together.
- Derive HTTP statuses only from `ErrorCode.http_status`; domain and application code never mention HTTP.
- Let the Ninja handler serialize `{code, message, details}`; API routers do not catch `DomainError` themselves.
- Web views catch only the refusals their page re-renders: `invalid_input` on a form, `has_dependents` and `forbidden` on a form or delete confirmation; `DomainErrorPagesMiddleware` turns every other code into its error page.
- Keep `details` to ids, field names and resource lists; never personal data.

<!-- aidd_rule_output:path=.claude/rules/06-design-patterns/6-domain-errors.md sha256=1531dbf403cd5456a5a20b5eac01efa07fda007d2de3d108695baa44bd0f9aac -->
