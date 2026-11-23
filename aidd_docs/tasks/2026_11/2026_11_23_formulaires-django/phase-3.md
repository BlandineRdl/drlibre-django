---
status: done
---

# Instruction: console screens
## Architecture projection
```txt
.
├── src/
│   └── drlibre/
│       └── interfaces/
│           └── web/
│               ├── forms/
│               │   └── console.py ✅
│               ├── presenters/
│               │   ├── staff.py ✏️
│               │   ├── waitlist.py ✏️
│               │   └── console_appointments.py ✏️
│               ├── templates/
│               │   └── console/
│               │       ├── form.html ✏️
│               │       ├── waitlist.html ✏️
│               │       └── appointment_cancel.html ✏️
│               └── views/
│                   ├── console_reference.py ✏️
│                   ├── console_users.py ✏️
│                   ├── console_clinicians.py ✏️
│                   ├── console_waitlist.py ✏️
│                   └── console_appointments.py ✏️
└── tests/
    ├── forms/
    │   └── test_console_forms.py ✅
    ├── api/
    │   └── test_console_reference.py ✏️
    └── presenters/
        ├── test_reference_presenters.py ✏️
        └── test_console_appointments_presenters.py ✏️
```
## Test Scope
| Scenario | Action | Observable outcome | Actor |
| --- | --- | --- | --- |
| Setup | `docker compose up -d` | stack up | system |
| Happy path | `uv run pytest tests/forms tests/presenters tests/api/test_console_reference.py tests/api/test_console_users.py tests/api/test_console_appointment_pages.py tests/api/test_console_supervision_pages.py tests/api/test_waitlist_pages.py tests/api/test_record_provenance.py` | hospitals, specialties, departments, rooms, types, users, clinicians, waitlist add and console cancel behave as before | cli |
| Edge case | invalid time zone, bad colour, latitude out of range, dependents on delete | message on the field and autofocus (`test_console_reference.py:118`), delete confirmation unchanged | cli |
| Teardown | none | stack left as found | system |

## Tasks to do
### `1)` Reference screens
> One `Form` per reference record replaces the `Screen.fields` tuples.

1. `forms/console.py`: `HospitalForm`, `SpecialtyForm`, `DepartmentForm`, `RoomForm`, `AppointmentTypeForm` with today's labels, help texts, `autocomplete`, select choices given at init, checkboxes as `BooleanField(required=False)`.
2. `views/console_reference.py`: `Screen` carries its form class instead of `fields`; save passes the posted strings of the form's fields to `screen.save.execute(fields=…)` once `is_valid()`.

### `2)` Users, clinicians, waitlist add, console cancel
> Same pattern for the remaining console forms.

1. `UserForm` (with `temporary_password` on create), `ClinicianProfileForm` (`user_id`, profile fields, `weight` optional), `WaitlistAddForm` (`patient_email` + join fields, reusing `WaitlistJoinForm` by inheritance), console cancel reusing `CancelForm`.
2. Migrate `views/console_users.py`, `console_clinicians.py`, `console_waitlist.py`, `console_appointments.py` and `presenters/staff.py`, `waitlist.py`, `console_appointments.py`; drop `USER_FIELDS`, `TEMPORARY_PASSWORD`, `PROFILE_FIELDS` (staff), `CLINICIAN_FIELD`, `ADD_FIELDS`, `_posted`.
3. Keep the book wizard `request.POST.dict()`, `start`, `week` direct.

### `3)` Tests
> Console forms locked.

0. First rewrite `tests/api/test_console_reference.py:118` order-independent.
1. `tests/forms/test_console_forms.py`: an invalid reference field is described, focused and summarised; a temporary password is never re-displayed.
2. Move `FieldView` assertions out of reference and console appointment presenter tests.

## Test acceptance criteria
| Task | Acceptance criteria |
| --- | --- |
| 1 | `tests/api/test_console_reference.py` passes, line 118 rewritten order-independent |
| 2 | console users, clinicians, waitlist and appointment page tests pass; no `FieldSpec` left in `views/` |
| 3 | `uv run pytest tests/forms tests/presenters` passes |
