---
status: done
---

# Instruction: base form, renderer, French, auth screens
## Architecture projection
```txt
.
├── config/
│   └── settings.py ✏️
├── static/
│   └── drlibre.css ✏️
├── src/
│   └── drlibre/
│       └── interfaces/
│           └── web/
│               ├── forms/ ✅
│               │   ├── __init__.py ✅
│               │   ├── base.py ✅
│               │   └── auth.py ✅
│               ├── presenters/
│               │   └── auth.py ✏️
│               ├── templates/
│               │   ├── forms/
│               │   │   └── form.html ✅
│               │   └── auth/
│               │       ├── form_page.html ✏️
│               │       └── link_continue.html ✏️
│               └── views/
│                   └── auth.py ✏️
└── tests/
    ├── forms/ ✅
    │   ├── __init__.py ✅
    │   └── test_auth_forms.py ✅
    └── presenters/
        └── test_auth_presenters.py ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d` | PostgreSQL, Redis, Mailpit up | system |
| Happy path | `uv run pytest tests/forms tests/presenters/test_auth_presenters.py tests/api/test_auth_endpoints.py tests/api/test_sign_in_link_endpoints.py` | sign-in, link request and password change behave as before | cli |
| Edge case | empty email, wrong password, short new password | French message on the field, `aria-invalid`, `aria-describedby`, summary link `#field-…`, autofocus on the first invalid field, password never re-displayed | cli |
| Edge case | `uv run pytest` after `LANGUAGE_CODE = "fr"` | no template shows a localised number or date that breaks a test or an input | cli |
| Teardown | none | stack left as found | system |

## Tasks to do
### `1)` Settings
> Django renders forms from project templates, in French.

1. Add `"django.forms"` to `INSTALLED_APPS`, set `FORM_RENDERER = "django.forms.renderers.TemplatesSetting"`.
2. Set `LANGUAGE_CODE = "fr"`; run `uv run pytest`; fix each localisation regression at its template (`unlocalize` or presenter-formatted string), never by reverting the language.

### `2)` Base form
> One base gives every form the current accessible markup.

1. `forms/base.py`: `WebForm(forms.Form)` with `auto_id = "field-%s"`, `template_name = "forms/form.html"`.
2. `refuse(error: DomainError)`: `INVALID_INPUT` details → `add_error(field, message)` per field (unknown field → `None`), other codes → `add_error(None, error.message)`.
3. After validation or `refuse`, the first field with errors gets `autofocus`.
4. Keep today's markup: « (facultatif) » after optional labels, empty select option « Choisir… », checkbox inside its `<label>`, `novalidate` on `<form>`; add `.errorlist` and `.helptext` rules to `static/drlibre.css` matching `.field-error` (line 101).
5. `forms/form.html`: error summary `role="alert"` linking `#field-<name>` with label and message when errors exist, then `{% for field in form %}{{ field.as_field_group }}{% endfor %}`; the page template keeps `<form>`, CSRF, hidden fields and buttons.

### `3)` Auth screens
> Sign-in, link request and password change use Django forms.

1. `forms/auth.py`: `SignInForm` (`EmailField` `email`, `CharField` `password` `PasswordInput`), `LinkRequestForm` (`link_email`), `PasswordChangeForm` (`current_password`, `new_password` 10-72, help text), widgets carrying today's `autocomplete`.
2. `views/auth.py`: bind to `request.POST`, call the use case only if `is_valid()`, `form.refuse(error)` on refusal, re-render; keep `next` and `token` direct reads.
3. `presenters/auth.py`: drop `SIGN_IN_FIELDS`, `LINK_FIELDS`, `PASSWORD_FIELDS`; page ViewModels carry title, action, submit label and the form.
4. Templates render `{{ form }}`.

### `4)` Tests
> Behaviour locked at the form level.

1. First rewrite `tests/api/test_auth_endpoints.py:136` and `tests/presenters/test_auth_presenters.py:37` to assert attributes in any order, with `field-x_error`/`field-x_helptext` ids.
2. `tests/forms/test_auth_forms.py`: refused sign-in keeps the email, never the password; an invalid field is described, focused and summarised; an untouched form shows no error and no focus.
3. Move the `FieldView` assertions out of `tests/presenters/test_auth_presenters.py` into those tests; keep the presenter tests on page ViewModels.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `uv run python manage.py check` passes; full suite green with `LANGUAGE_CODE = "fr"` |
| 2 | a bound invalid `WebForm` renders `id="field-x"`, `aria-invalid="true"`, `aria-describedby` with `field-x_error`, `autofocus` on the first invalid field only, a summary link `href="#field-x"` |
| 3 | auth page and link tests pass; no `request.POST` read left in `views/auth.py` but `next` and `token` |
| 4 | `uv run pytest tests/forms tests/presenters/test_auth_presenters.py` passes |
