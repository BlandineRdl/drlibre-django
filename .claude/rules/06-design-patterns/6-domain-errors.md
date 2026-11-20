---
paths:
  - "src/drlibre/**/*.py"
---
# Domain errors
- Signal an expected failure by raising `DomainError(ErrorCode.<CODE>, message, details)` or returning `Err`; never raise bare exceptions for business outcomes.
- Use only `ErrorCode` members from spec 4; add a code to the spec, the enum and `_HTTP_STATUS` together.
- Derive HTTP statuses only from `ErrorCode.http_status`; domain and application code never mention HTTP.
- Let the Ninja handler serialize `{code, message, details}`; interfaces do not catch `DomainError` themselves.
- Keep `details` to ids, field names and resource lists; never personal data.

<!-- aidd_rule_output:path=.claude/rules/06-design-patterns/6-domain-errors.md sha256=120b97df21950952547f1f28435d9d024850effe77e70989154930e7b9faa761 -->
