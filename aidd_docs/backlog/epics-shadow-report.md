---
source: aidd_docs/backlog/epics/
generated_at: 2026-11-20
---

# Shadow Areas Report
Source: `aidd_docs/backlog/epics/`
Generated: `2026-11-20`

Total gaps: 19 | Blocker: 0 | Major: 14 | Minor: 5

---

## Warnings
- The source is a folder: the 8 Epics and the 10 Stories of Epic 1 (`aidd_docs/backlog/stories/`) are scanned as one set, against `aidd_docs/memory/external/drlibre-specs.md`, `aidd_docs/INSTALL.md` and `aidd_docs/memory/testing.md`.

---

## Gaps by Category
### unstated assumption
**[major]** Where does a clinician or an admin change their own password?
> §8 Profile: "Change password needs the current password and a different new one of 10 to 72 characters"

**[major]** Is Epic 3's booking confirmation email the same message as Epic 4's "Appointment booked" notification email, so one booking sends one email?
> E3: "Emails de code, de lien de connexion et de confirmation" / E4: "Email pour chaque notification patient"

### ambiguous term
**[major]** What makes the admin-issued password temporary: a forced change at first sign-in, an expiry, or nothing?
> §10 Users: "Create with name, email, role and a temporary password"

**[major]** How does a visitor give their location for the distance sort: browser geolocation, a typed address, or a chosen city?
> §6.4: "Distance, nearest first, only when the visitor gave a location"

**[major]** Is the clinician of a "first available" booking picked when the hold is created or when the code is verified?
> §3.1 Booking hold: "clinician, appointment type, start, end, the details the visitor typed, expiry"

**[minor]** Does "weight above 0" in round robin matter when the profile weight is at least 1?
> §5.5: "active clinicians of the type's department with weight above 0"

### missing edge case
**[major]** What happens to an `OFFERED` waitlist entry when its offered slot starts without being accepted?
> §5.8: "Expiry. A `WAITING` entry whose latest time has passed becomes `EXPIRED`."

**[major]** What happens to the future `BOOKED` appointments of a clinician who is deactivated?
> §5.2: "the clinician's user is active"

**[minor]** Can a patient withdraw their own waitlist entry before it expires?
> §8 Waitlist: "Form to join ... and the list of own entries with status"

**[minor]** What happens to future appointments when the availability rule that contains them is edited or deleted?
> §9 Availability: "List, create, edit and delete own availability rules"

### missing actor
**[major]** Which process expires booking holds and writes the "hold expired" audit entry?
> §7.7: "Hold created, hold expired, code verification failed ... are all audited"

### missing failure mode
**[major]** When the code is correct but placement fails (`conflict`, `rule_violation`, `no_clinician_available`), is the patient account still created and a session still opened?
> §7.1 step 6: "The correct code also signs the patient in with a 24 hour session"

**[major]** Should a hold or a booking be rolled back when its email (code or confirmation) cannot be sent?
> §4: "One transaction per logical change, including its audit entry and notifications"

### missing acceptance criterion
**[major]** What request limit per network address applies to holds, code requests and sign-in link requests?
> §7.5: "rate limited per email address and per network address"

**[minor]** Should Epic 2's availability and calendar screens carry the WCAG 2.2 AA and 375–1440 px evidence like the other Epics?
> E2 Success Evidence: no accessibility or viewport line

**[minor]** How is "the same time" measured between an unknown email and a wrong password?
> S1: "Un email inconnu et un mauvais mot de passe donnent le même message, dans le même temps de réponse."

### missing dependency
**[major]** Which Epic owns the precomputed `slot` table, and which events refresh it?
> INSTALL.md: "PostgreSQL 17 with a transactional `slot` table ... precomputed slots make next-availability search a few-ms indexed query"

**[major]** Which Epic delivers the existing application API endpoints `POST /auth/login`, `POST /auth/logout`, `GET /appointments` and `POST /appointments` for a signed-in caller?
> §14 [existing]; E3 covers only "API publique correspondante (§14 [new])"

**[major]** Which Epic builds the load-test seed (10 hospitals, 200 clinicians, 5k patients, 50k appointments) that Epic 3's p95 evidence relies on?
> INSTALL.md Testing strategy 8: "Locust scenarios on search and booking against the demo seed (10 hospitals, 200 clinicians, 5k patients, 50k appointments"
