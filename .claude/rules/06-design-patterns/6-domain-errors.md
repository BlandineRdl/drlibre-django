---
paths:
  - "src/drlibre/**/*.py"
---
# Domain errors
- Signal an expected failure by raising `DomainError(ErrorCode.<CODE>, message, details)`; never raise bare exceptions for business outcomes.
- Use only `ErrorCode` members from spec 4; add a code to the spec, the enum and `_HTTP_STATUS` together.
- Derive HTTP statuses only from `ErrorCode.http_status`; domain and application code never mention HTTP.
- Let the Ninja handler serialize `{code, message, details}`; API routers do not catch `DomainError` themselves.
- Web views catch only the refusals their page re-renders: `invalid_input` on a form, `has_dependents` and `forbidden` on a form or delete confirmation, booking, portal and waitlist pages also `rule_violation`, `invalid_transition`, `conflict`, `no_clinician_available` and `no_room_available` inline, waitlist pages also `not_found` on a join or a manual offer; `DomainErrorPagesMiddleware` turns every other code into its error page.
- Keep `details` to ids, field names and resource lists; never personal data.

<!-- aidd_rule_output:path=.claude/rules/06-design-patterns/6-domain-errors.md sha256=e7517d7694fadc853d36f9d0ecb5462ea2f4a91468d94273f4554a787237e096 -->
