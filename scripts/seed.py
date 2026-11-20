import os
from collections.abc import Callable
from typing import Any

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import structlog  # noqa: E402
from django.db import transaction  # noqa: E402

from drlibre.bootstrap.container import Container, container  # noqa: E402
from drlibre.organisation.application.ports.inbound import SaveRecord  # noqa: E402
from drlibre.shared_kernel.ids import Id  # noqa: E402
from drlibre.shared_kernel.pagination import Page, PageRequest  # noqa: E402

logger = structlog.get_logger("drlibre.seed")

# Fictitious demo sign-ins, localhost only; documented in README.md.
DEMO_PASSWORD = "drlibre-demo-2026"  # noqa: S105
_TEMPORARY = "drlibre-temporary-2026"

HOSPITALS = (
    {
        "code": "HNORD",
        "name": "Hôpital Nord",
        "street": "2 avenue Oscar Lambret",
        "postal_code": "59000",
        "city": "Lille",
        "country": "France",
        "phone": "+33 3 20 00 00 00",
        "time_zone": "Europe/Paris",
        "latitude": "50.61",
        "longitude": "3.03",
    },
    {
        "code": "HATL",
        "name": "Hôpital Atlantique",
        "street": "Route de Chauvel",
        "postal_code": "97139",
        "city": "Les Abymes",
        "country": "France",
        "phone": "+590 590 00 00 00",
        "time_zone": "America/Guadeloupe",
    },
)
SPECIALTIES = ({"code": "CARDIO", "name": "Cardiologie"}, {"code": "PEDIA", "name": "Pédiatrie"})
DEPARTMENTS = (
    {"code": "HNORD-CARD", "name": "Cardiologie", "hospital": "HNORD"},
    {"code": "HNORD-PEDIA", "name": "Pédiatrie", "hospital": "HNORD"},
    {"code": "HATL-CARD", "name": "Cardiologie", "hospital": "HATL"},
)
ROOMS = (
    {
        "code": "HNORD-C101",
        "name": "Consultation 101",
        "department": "HNORD-CARD",
        "floor": "1",
        "capacity": "1",
        "equipment": "ECG, Tensiomètre",
    },
    {
        "code": "HNORD-P201",
        "name": "Consultation 201",
        "department": "HNORD-PEDIA",
        "floor": "2",
        "capacity": "2",
        "equipment": "Table à langer",
    },
    {
        "code": "HATL-C001",
        "name": "Consultation 001",
        "department": "HATL-CARD",
        "floor": "0",
        "capacity": "1",
        "equipment": "ECG",
    },
)
TYPES = (
    {
        "code": "HNORD-CONSULT",
        "name": "Consultation de cardiologie",
        "department": "HNORD-CARD",
        "duration_minutes": "30",
        "buffer_minutes": "5",
        "colour": "#1D4E89",
    },
    {
        "code": "HNORD-PEDIA",
        "name": "Consultation pédiatrique",
        "department": "HNORD-PEDIA",
        "duration_minutes": "20",
        "buffer_minutes": "0",
        "colour": "#2E7D32",
    },
    {
        "code": "HATL-CONSULT",
        "name": "Consultation de cardiologie",
        "department": "HATL-CARD",
        "duration_minutes": "30",
        "buffer_minutes": "10",
        "colour": "#8E24AA",
    },
)
USERS = (
    ("ADMIN", "Alice Admin", "admin@drlibre.localhost"),
    ("CLINICIAN", "Dr Claire Martin", "clinicien@drlibre.localhost"),
    ("PATIENT", "Paul Patient", "patient@drlibre.localhost"),
)


def _by_code(page: Callable[[PageRequest], Page[Any]], code: str) -> Id | None:
    items = page(PageRequest(search=code)).items
    return next((r.id for r in items if r.code == code), None)


def _upsert(
    save: SaveRecord, page: Callable[[PageRequest], Page[Any]], fields: dict[str, str]
) -> Id:
    """Get or create on the unique code, so a second run adds nothing."""
    found = _by_code(page, fields["code"])
    return found or save.execute(actor=None, record_id=None, fields={**fields, "active": "on"})


def seed_referential(app: Container) -> None:
    q = app.reference_queries
    hospitals = {h["code"]: _upsert(app.save_hospital, q.hospitals, h) for h in HOSPITALS}
    for specialty in SPECIALTIES:
        _upsert(app.save_specialty, q.specialties, specialty)
    departments = {
        d["code"]: _upsert(
            app.save_department, q.departments, {**d, "hospital_id": str(hospitals[d["hospital"]])}
        )
        for d in DEPARTMENTS
    }
    for room in ROOMS:
        fields = {**room, "department_id": str(departments[room["department"]])}
        _upsert(app.save_room, q.rooms, fields)
    for kind in TYPES:
        fields = {
            **kind,
            "department_id": str(departments[kind["department"]]),
            "needs_room": "on",
            "bookable_online": "on",
        }
        _upsert(app.save_appointment_type, q.appointment_types, fields)


def _user_id(app: Container, email: str) -> Id | None:
    items = app.user_queries.users(PageRequest(search=email)).items
    return next((u.id for u in items if u.email.value == email), None)


def seed_users(app: Container) -> None:
    for role, name, email in USERS:
        if _user_id(app, email) is not None:
            continue
        user_id = app.save_user.execute(
            actor=None,
            user_id=None,
            full_name=name,
            email=email,
            role=role,
            active=True,
            temporary_password=_TEMPORARY,
        )
        app.change_password.execute(
            user_id=user_id, current_password=_TEMPORARY, new_password=DEMO_PASSWORD
        )


def seed_clinician_profile(app: Container) -> None:
    clinician = _user_id(app, "clinicien@drlibre.localhost")
    q = app.reference_queries
    if clinician is None or clinician in q.profiled_user_ids():
        return
    fields = {
        "department_id": str(_by_code(q.departments, "HNORD-CARD")),
        "specialty_id": str(_by_code(q.specialties, "CARDIO")),
        "default_room_id": str(_by_code(q.rooms, "HNORD-C101")),
        "title": "Dr Claire Martin",
        "bio": "Cardiologue, consultations adultes.",
    }
    app.attach_clinician_profile.execute(actor=None, user_id=str(clinician), fields=fields)


# Each seeder gets or creates its rows, so the whole seed can run again safely.
SEEDERS: list[Callable[[Container], None]] = [seed_referential, seed_users, seed_clinician_profile]


def main() -> None:
    app = container()
    with transaction.atomic():
        for seeder in SEEDERS:
            seeder(app)
    logger.info("seed_done", seeders=len(SEEDERS))


if __name__ == "__main__":
    main()
