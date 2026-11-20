---
status: pending
---

# Instruction: Cross-cutting HTTP concerns
## Architecture projection
> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
config/
├── middleware.py        ✅  CorrelationIdMiddleware
├── logging.py           ✅  structlog JSON config
└── settings.py          ✅  middleware order, LOGGING, security headers, SECURE_CSP
tests/integration/test_http_headers.py ✅  Django test client
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | Django test client | app loaded | api |
| Happy path | request with `x-correlation-id: abc` | response header `x-correlation-id: abc`; log line JSON with `correlation_id: "abc"` | api |
| Edge case | request without header, or an invalid one (non-printable, > 128 chars) | a generated UUID4 is returned | api |
| Edge case | any response | `Content-Security-Policy` has `frame-ancestors 'none'`; `X-Frame-Options: DENY`; `X-Content-Type-Options: nosniff`; `Referrer-Policy` set | api |
| Teardown | clear structlog contextvars | none leaks to next request | system |

## Tasks to do
### `1)` Correlation id
> Every request has one id, echoed and logged.

1. Middleware reads `x-correlation-id`, validates it, else generates UUID4.
2. Binds it with `structlog.contextvars.bind_contextvars`, clears at request end.
3. Sets it on the response header.

### `2)` JSON logs
> structlog renders JSON for app and Django loggers.

1. `structlog.configure` with `merge_contextvars`, ISO timestamp, level, `JSONRenderer`.
2. Django `LOGGING` routes stdlib loggers through `structlog.stdlib.ProcessorFormatter`.
3. One request log line per request (method, path, status, duration) without query string or body.

### `3)` Security headers and CSP
> Standard headers, framing forbidden.

1. Django 6.x built-in CSP middleware and `SECURE_CSP` (verify names in Django 6.1 docs): `default-src 'self'`, `frame-ancestors 'none'`.
2. `X_FRAME_OPTIONS = "DENY"`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`, `SECURE_CROSS_ORIGIN_OPENER_POLICY`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | header echoed when valid, generated otherwise |
| 2 | captured log line parses as JSON and holds the request's correlation id |
| 3 | health response carries CSP with `frame-ancestors 'none'` and the listed headers |
