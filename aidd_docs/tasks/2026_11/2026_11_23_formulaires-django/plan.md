---
objective: "Every web form is a `django.forms.Form` rendered by Django's form templates, validated by the form then by the use case, with the current accessible markup kept, and the home-grown `FieldSpec`/`build_form` layer gone."
status: implemented
---

# Plan: formulaires Django
Source: request « Aucun django.forms : 32 lectures directes de request.POST, validées par les use cases et Pydantic. On perd le rendu et la gestion d'erreurs des formulaires que Django offre gratuitement. On devrait le mettre en place », clarified « le but est de pas réinventer la roue et d'utiliser ce que propose Django », validation choice: form and use cases

## Phases
| # | Phase | File | Depends on |
| --- | --- | --- | --- |
| 1 | Base form, renderer, French, auth screens | [`phase-1.md`](./phase-1.md) | none |
| 2 | Visitor, patient and clinician screens | [`phase-2.md`](./phase-2.md) | 1 |
| 3 | Console screens | [`phase-3.md`](./phase-3.md) | 2 |
| 4 | Remove the home-grown layer, docs, gates | [`phase-4.md`](./phase-4.md) | 3 |

## External sources
| URL | What it settled |
| --- | --- |
| https://docs.djangoproject.com/en/6.1/ref/forms/renderers/ | `TemplatesSetting` loads form templates through `TEMPLATES`, so project templates override `django/forms/*.html`; `django.forms` must be in `INSTALLED_APPS` for the built-in ones; confirmed in `.venv/.../django/forms/renderers.py:70` |
| https://docs.djangoproject.com/en/6.1/ref/forms/api/#django.forms.Form.add_error | `add_error(field, message)` attaches a use case refusal to a field, `None` for a form error |

## Impact
| Category | Verdict and evidence | Handled in |
| --- | --- | --- |
| runtime | Django 6.1.3 installed; `BoundField` sets `aria-invalid` and `aria-describedby` (`{auto_id}_helptext`, `{auto_id}_error`) itself (`boundfield.py:296-315`), error list carries `id="{field_id}_error"` (`errors/list/ul.html`); observed | 1 |
| runtime | `LANGUAGE_CODE = "en-us"` (`config/settings.py:147`): Django messages come out in English (« Ensure this value has at most 3 characters », observed by a run); switching to `fr` makes `DateInput` render `DATE_INPUT_FORMATS[0]` (`02/01/2026`), which `type="date"` refuses: every date widget needs `format="%Y-%m-%d"`; other localisation effects unverified until the suite runs (search coordinates are already strings, `presenters/search.py:358`) | 1 |
| runtime | `INSTALLED_APPS` lacks `django.forms` and no `FORM_RENDERER` is set (`config/settings.py:39,89`); observed | 1 |
| regression | the form layer is `presenters/forms.py` (`FieldSpec`, `build_form`, `FormView`, `field_messages`), about 175 lines in 14 Python files and 12 templates including `_form.html` (count unverified); markup locked by page tests (`id="field-…"`, `aria-invalid`, `autofocus`, summary `href="#field-…"`, `id="error-reason"` in `tests/api/test_booking_pages.py:144,160`, `test_workspace_pages.py:168-194`, `test_console_reference.py:118`, `test_workspace_availability.py:57`, `test_waitlist_pages.py:68`, `tests/use_cases/booking/test_le_patient_annule_un_rendez_vous.py:27-45`, `tests/use_cases/identity/test_le_patient_met_a_jour_son_profil.py:216-236`), e2e locators `#field-link_email` etc., presenter tests on `FieldView.autofocus`/`described_by` (`tests/presenters/test_auth_presenters.py:27-63`, booking, workspace); risk medium, observed in a Django probe: `auto_id="field-%s"` keeps the ids, but help and error ids become `field-x_helptext`/`field-x_error` and Django orders attributes `autofocus required aria-invalid aria-describedby id`, so regexes in `test_booking_pages.py:144-145,160`, `test_auth_endpoints.py:136`, `test_le_patient_met_a_jour_son_profil.py:237`, `test_console_reference.py:118`, `test_workspace_availability.py:57`, `test_workspace_pages.py:181,194` and presenter tests `test_auth_presenters.py:37`, `test_booking_presenters.py:80` break; no safety-net phase: each phase first rewrites its assertions order-independent (same attributes, any order), then migrates | 1, 2, 3, 4 |
| architecture | from: presenters build `FormView` dataclasses from `FieldSpec` tuples, views read `request.POST` (32 reads, 10 views), use cases validate strings through `FieldErrors`; to: `interfaces/web/forms/` holds one `Form` per screen, views bind it to `request.POST`, call the use case only when `is_valid()`, map a `DomainError` back with `add_error`; presenters keep page ViewModels (title, action, submit label, cancel) carrying the bound form; use case signatures and API/FHIR untouched | 1 |
| documentation | `aidd_docs/memory/architecture.md` (web forms decision, language), `codebase-map.md` (`interfaces/web/forms/`), `testing.md` (form tests layer) | 4 |

## Rules
| Rule | Why it applies |
| --- | --- |
| `aidd_docs/rules/00-architecture/0-interfaces-no-business-rule.md` | a form checks input shape (required, length, type) only; roles, lead times, windows and limits stay in use cases |
| `aidd_docs/rules/06-design-patterns/6-domain-errors.md` | views keep catching the same refusals inline, now through `add_error` |
| `aidd_docs/rules/05-testing/5-acceptance-test-names.md` | form test names state the observable behaviour |
| Architecture « use cases validate every boundary » | use cases keep their `FieldErrors` checks: API and FHIR reach them without a form |
| Architecture « WCAG 2.2 AA, templates hold no business logic » | the error summary, `aria-*` and first-error autofocus survive the switch |

## Decisions
| Decision | Why |
| --- | --- |
| Use `django.forms` for collection, input validation and rendering | user's goal: use what Django offers instead of `FieldSpec`/`build_form` |
| Form and use case both validate | chosen by the user; input shape duplicated on purpose for the web, use cases stay the authority for API and FHIR; a use case refusal still reaches the field through `add_error` |
| `LANGUAGE_CODE = "fr"` | Django's built-in messages in French, matching `FieldErrors` (« Ce champ est obligatoire. »); localisation side effects fixed where tests show them |
| Base `WebForm(forms.Form)`: `auto_id="field-%s"`, `refuse(error)`, first-error `autofocus`, project `template_name` | keeps the ids tests and e2e rely on, one place for the summary and focus |
| `FORM_RENDERER = "django.forms.renderers.TemplatesSetting"`, project overrides of `django/forms/field.html` only where Pico needs it | Django's own templates otherwise, no wheel reinvented |
| Use case signatures unchanged: views pass `cleaned_data` when its type matches the parameter, the posted string otherwise | API and FHIR keep calling them with strings; no change outside `interfaces/web` |
| Control values (`next`, `token`, `start`, `week`, `from`, GET-or-POST choices, book wizard `request.POST.dict()`) stay direct reads | hidden or navigation values, no visible field |
| Phases run in sequence | phases 2 and 3 share `console/form.html` (rendered by `views/workspace_availability.py:57`) and `presenters/waitlist.py` |
| `Choice`/`ChoiceView` move to `presenters/choices.py` | they also serve non-form selects: `presenters/console_audit.py:9,25,82`, `console_appointments.py` filters and book wizard, `waitlist.py:94,262` status filter |
