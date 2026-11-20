<!-- aidd_rule:{"version":1,"category":"06-design-patterns","slug":"6-domain-errors","description":"Raising and mapping expected failures with ErrorCode","paths":["src/drlibre/**/*.py"],"targets":["claude"]} -->
# Domain errors
- Signal an expected failure by raising `DomainError(ErrorCode.<CODE>, message, details)`; never raise bare exceptions for business outcomes.
- Use only `ErrorCode` members from spec 4; add a code to the spec, the enum and `_HTTP_STATUS` together.
- Derive HTTP statuses only from `ErrorCode.http_status`; domain and application code never mention HTTP.
- Let the Ninja handler serialize `{code, message, details}`; interfaces do not catch `DomainError` themselves.
- Keep `details` to ids, field names and resource lists; never personal data.
