---
paths:
  - "src/drlibre/interfaces/**/*.py"
  - "src/drlibre/interfaces/**/*.html"
  - "src/drlibre/shared_kernel/booking_policy.py"
---
# Interfaces hold no business rule
- Never decide a role, lead time, window or limit in a view, router, presenter or template.
- Call one use case and map its result or its `DomainError`.
- Enforce each rule once, in a use case or the domain.
- Declare each policy constant shared across contexts or layers once in `shared_kernel/booking_policy.py`.
- Keep a constant used only inside one context's core in that core.
- Never repeat a policy number as a literal, in code or in text.
- Format display text from the policy constants, such as the lead time in hours.
- Pass a window computed by a use case to the template; never recompute it in a view.
- Offer an action only when every rule its use case applies would accept it now; derive it in the domain, never in a template.

<!-- aidd_rule_output:path=.claude/rules/00-architecture/0-interfaces-no-business-rule.md sha256=c4c21a92516b469dd44083907e0f8a2392b56a70c693cec1764bae24a3be6f18 -->
