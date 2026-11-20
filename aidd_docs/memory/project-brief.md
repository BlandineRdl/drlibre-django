# Project Brief
## Purpose
- Hospital appointment scheduling: public search, booking without an account, patient, clinician and admin workspaces, FHIR R4 API.
- Portfolio sandbox showcasing a hexagonal, BDD-driven Django back end; fictitious data, localhost only.
- Functional source of truth: `aidd_docs/memory/external/drlibre-specs.md`.

## Users
- Visitor: searches, books by verifying an email code.
- Patient: signs in by email link or password, manages own appointments and waitlist.
- Clinician: runs own agenda, notes, availability and time off.
- Admin: global across hospitals, manages waitlist, audit log and dashboard.
- API client: bearer token carrying one user's rights.

## Main journey
1. A visitor searches and picks a free slot.
2. Their details create a 10-minute booking hold.
3. The emailed 6-digit code books the appointment.
4. It creates the passwordless patient if needed and opens a 24-hour session.
5. The patient lands on their appointments.

## Domain language
| Term | Meaning |
| --- | --- |
| Clinician | Practitioner; shown publicly as "provider" |
| Passwordless patient | Patient signing in only by email link |
| Booking hold | Temporary slot reservation during email verification; counts as a conflict |
| Slot | Free start time from availability, time off and active appointments |
| Active appointment | Not `CANCELLED` or `NO_SHOW` |
| Source | `ONLINE`, `ROUND_ROBIN` (first available) or `STAFF` |
| Round robin | Weighted "first available" assignment within a department |
| Waitlist offer | Freed slot offered to the oldest matching entry; reserves nothing |

## Key features
| Feature | Entry |
| --- | --- |
| Search, anonymous booking | spec 6, 7 |
| Patient, clinician workspaces | spec 8, 9 |
| Admin, reporting | spec 10, 13 |
| API, FHIR | spec 14, 15 |

## Business rules
- Patients book 120 minutes ahead, cancel or reschedule 24 hours ahead, hold at most 3 open online bookings.
- Every write is audited in its transaction; audit metadata holds no personal data.
- Identity comes from the session or token, never the request body.
- The end time is never accepted from the caller.
- Every booking path runs the same placement steps.
- Responses never reveal whether an email has an account.

## Out of scope
- Text messages, payments, hospital-scoped admins, self sign-up, patients setting a password, real data or HDS, SEO.
