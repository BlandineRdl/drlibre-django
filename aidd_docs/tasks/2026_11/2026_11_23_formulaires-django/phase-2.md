---
status: done
---

# Instruction: visitor, patient and clinician screens
## Architecture projection
```txt
.
├── src/
│   └── drlibre/
│       └── interfaces/
│           └── web/
│               ├── forms/
│               │   ├── booking.py ✅
│               │   ├── portal.py ✅
│               │   └── workspace.py ✅
│               ├── presenters/
│               │   ├── booking.py ✏️
│               │   ├── portal.py ✏️
│               │   ├── waitlist.py ✏️
│               │   ├── workspace.py ✏️
│               │   └── availability.py ✏️
│               ├── templates/
│               │   ├── booking/
│               │   │   ├── details.html ✏️
│               │   │   └── code.html ✏️
│               │   ├── portal/
│               │   │   ├── cancel.html ✏️
│               │   │   ├── profile.html ✏️
│               │   │   └── waitlist.html ✏️
│               │   └── workspace/
│               │       ├── cancel.html ✏️
│               │       └── appointment.html ✏️
│               └── views/
│                   ├── booking.py ✏️
│                   ├── portal.py ✏️
│                   ├── workspace.py ✏️
│                   └── workspace_availability.py ✏️
└── tests/
    ├── forms/
    │   ├── test_booking_forms.py ✅
    │   ├── test_portal_forms.py ✅
    │   └── test_workspace_forms.py ✅
    ├── presenters/
    │   ├── test_booking_presenters.py ✏️
    │   ├── test_portal_presenters.py ✏️
    │   ├── test_waitlist_presenters.py ✏️
    │   ├── test_availability_presenters.py ✏️
    │   └── test_workspace_presenters.py ✏️
    ├── api/
    │   ├── test_booking_pages.py ✏️
    │   ├── test_workspace_availability.py ✏️
    │   └── test_workspace_pages.py ✏️
    └── use_cases/
        ├── booking/
        │   └── test_le_patient_annule_un_rendez_vous.py ✏️
        └── identity/
            └── test_le_patient_met_a_jour_son_profil.py ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d` | stack up | system |
| Happy path | `uv run pytest tests/forms tests/presenters tests/api/test_booking_pages.py tests/api/test_portal_pages.py tests/api/test_waitlist_pages.py tests/api/test_workspace_pages.py tests/api/test_workspace_availability.py tests/use_cases` | booking, code, cancel, profile, waitlist join, notes, availability and time off behave as before | cli |
| Edge case | missing name, wrong code, reason over the limit, inverted waitlist dates, rule end before start | message on the field, same status, summary link, first-error autofocus | cli |
| Teardown | none | stack left as found | system |

## Tasks to do
### `1)` Booking
> Details and code forms.

0. Every `DateInput`/`DateTimeInput` gets `format="%Y-%m-%d"` (`%Y-%m-%dT%H:%M` for datetime-local) so `type="date"` keeps its value under `LANGUAGE_CODE = "fr"`.
1. `forms/booking.py`: `DetailsForm` (`full_name`, `birth_date` `DateField`, `email`, `phone` optional, `reason` optional textarea, `accepted_terms` `BooleanField`), `CodeForm` (`code`).
2. `views/booking.py`, `presenters/booking.py`: bind, `is_valid()`, `refuse`, drop `DETAILS_FIELDS`, `CODE_FIELDS`; keep the GET-or-POST slot `data` direct.

### `2)` Cancel, notes, profile, waitlist join
> One reason form shared by the three cancel pages.

1. `forms/portal.py`: `CancelForm` (`reason`, `max_length=MAX_CANCELLATION_REASON`), `ProfileForm` (`phone`, `birth_date`, optional), `WaitlistJoinForm` (`appointment_type_id`, `clinician_id` choices given at init, `from_date`, `to_date`).
2. `forms/workspace.py`: `NotesForm` (`clinical_notes`, `max_length=MAX_CLINICAL_NOTES`), `RuleForm`, `TimeOffForm` (help naming the clinician's zone, given at init).
3. Migrate `views/portal.py`, `views/workspace.py`, `views/workspace_availability.py` and their presenters; drop `REASON_FIELD`, `PROFILE_FIELDS` (portal), `JOIN_FIELDS`, `NOTES_FIELD`, `rule_fields`, `time_off_fields`, `_posted`; `ADD_FIELDS` stays for phase 3 if still referenced.
4. Keep `start`, `week`, `from` direct reads.

### `3)` Tests
> Error ids follow Django.

1. Before migrating, rewrite to order-independent attribute checks with `field-x_error` ids: `test_booking_pages.py:144-145,160`, `test_le_patient_met_a_jour_son_profil.py:237`, `test_workspace_pages.py:181,194`, `test_workspace_availability.py:57`, `test_le_patient_annule_un_rendez_vous.py:45`, `test_booking_presenters.py:80`.
2. Move `FieldView` assertions of booking, portal, waitlist, availability and workspace presenter tests into `tests/forms/`.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | rewritten `tests/api/test_booking_pages.py:144-145,160` pass; a re-rendered `birth_date` keeps `value="YYYY-MM-DD"` |
| 2 | portal, waitlist, workspace and availability page tests pass; no `build_form` call left in these views and presenters |
| 3 | `uv run pytest tests/forms tests/presenters tests/use_cases tests/api` passes |
