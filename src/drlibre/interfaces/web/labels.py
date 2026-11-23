from drlibre.identity.application.ports.inbound import Role

# Weekdays numbered 0 Sunday to 6 Saturday (spec 3.1), shown Monday first.
WEEK_ORDER = (1, 2, 3, 4, 5, 6, 0)
ROLE_LABELS = {Role.ADMIN: "Admin", Role.CLINICIAN: "Praticien", Role.PATIENT: "Patient"}
