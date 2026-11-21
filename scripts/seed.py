import argparse
import os
import random
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import structlog  # noqa: E402
from django.db import transaction  # noqa: E402

from drlibre.booking.infrastructure.django.models import AppointmentRecord  # noqa: E402
from drlibre.bootstrap.container import Container, container  # noqa: E402
from drlibre.identity.infrastructure.django.models import UserRecord  # noqa: E402
from drlibre.organisation.application.ports.inbound import SaveRecord  # noqa: E402
from drlibre.organisation.infrastructure.django.models import (  # noqa: E402
    AppointmentTypeRecord,
    ClinicianProfileRecord,
    DepartmentRecord,
    HospitalRecord,
    RoomRecord,
    SpecialtyRecord,
)
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel  # noqa: E402
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
ADMIN_EMAIL = "admin@drlibre.localhost"
VISITOR_EMAIL = "visiteur@drlibre.localhost"
USERS = (
    ("ADMIN", "Alice Admin", ADMIN_EMAIL),
    ("CLINICIAN", "Dr Claire Martin", "clinicien@drlibre.localhost"),
    ("PATIENT", "Paul Patient", "patient@drlibre.localhost"),
)


def _by_code(page: Callable[[PageRequest], Page[Any]], code: str) -> Id | None:
    items = page(PageRequest(search=code)).items
    return next((r.id for r in items if r.code == code), None)


def _upsert(
    save: SaveRecord,
    page: Callable[[PageRequest], Page[Any]],
    fields: dict[str, str],
    *,
    actor: Id | None,
) -> Id:
    """Get or create on the unique code, so a second run adds nothing."""
    found = _by_code(page, fields["code"])
    return found or save.execute(actor=actor, record_id=None, fields={**fields, "active": "on"})


def _demo_admin(app: Container) -> Id | None:
    """The demo admin is the actor of every seeded write once it exists (spec §3.1)."""
    return _user_id(app, ADMIN_EMAIL)


def seed_referential(app: Container) -> None:
    q = app.reference_queries
    actor = _demo_admin(app)
    hospitals = {
        h["code"]: _upsert(app.save_hospital, q.hospitals, h, actor=actor) for h in HOSPITALS
    }
    for specialty in SPECIALTIES:
        _upsert(app.save_specialty, q.specialties, specialty, actor=actor)
    departments = {
        d["code"]: _upsert(
            app.save_department,
            q.departments,
            {**d, "hospital_id": str(hospitals[d["hospital"]])},
            actor=actor,
        )
        for d in DEPARTMENTS
    }
    for room in ROOMS:
        fields = {**room, "department_id": str(departments[room["department"]])}
        _upsert(app.save_room, q.rooms, fields, actor=actor)
    for kind in TYPES:
        fields = {
            **kind,
            "department_id": str(departments[kind["department"]]),
            "needs_room": "on",
            "bookable_online": "on",
        }
        _upsert(app.save_appointment_type, q.appointment_types, fields, actor=actor)


def _user_id(app: Container, email: str) -> Id | None:
    items = app.user_queries.users(PageRequest(search=email)).items
    return next((u.id for u in items if u.email.value == email), None)


def seed_users(app: Container) -> None:
    for role, name, email in USERS:
        if _user_id(app, email) is not None:
            continue
        # The first account, the demo admin, has no one before it to act.
        user_id = app.save_user.execute(
            actor=_demo_admin(app),
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
    app.attach_clinician_profile.execute(
        actor=_demo_admin(app), user_id=str(clinician), fields=fields
    )


# Monday to Friday, local time of the hospital; weekday 0 is Sunday (spec §3.1).
DEMO_RULES = tuple(
    {"weekday": str(day), "start": start, "end": end, "step_minutes": "30"}
    for day in range(1, 6)
    for start, end in (("09:00", "12:00"), ("14:00", "17:00"))
)


def seed_availability(app: Container) -> None:
    clinician = _user_id(app, "clinicien@drlibre.localhost")
    profile = app.reference_queries.clinician_profile_of(clinician) if clinician else None
    if clinician is None or profile is None:
        return
    existing = {
        (str(r.weekday), f"{r.start:%H:%M}") for r in app.availability_queries.rules_of(profile.id)
    }
    for rule in DEMO_RULES:
        if (rule["weekday"], rule["start"]) not in existing:
            app.save_availability_rule.execute(actor=clinician, rule_id=None, fields=rule)


def seed_passwordless_patient(app: Container) -> None:
    """A patient who signs in only by email link (spec §3.1), as a booking visitor becomes."""
    now = datetime.now(UTC)
    UserRecord.objects.get_or_create(
        email=VISITOR_EMAIL,
        defaults={
            "full_name": "Victor Visiteur",
            "role": "PATIENT",
            "active": True,
            "email_verified_at": now,
            "created_at": now,
            "updated_at": now,
        },
    )


# Load size, bulk inserts through the ORM: 50k rows through the use cases would take hours.
LOAD_HOSPITALS = 8
LOAD_DEPARTMENTS_PER_HOSPITAL = 2
LOAD_SPECIALTIES = ("CARDIO", "PEDIA", "DERMA", "ORTHO", "NEURO")
LOAD_CLINICIANS = 200
LOAD_PATIENTS = 5000
LOAD_APPOINTMENTS_PER_CLINICIAN = 250
LOAD_TIME_ZONE = ZoneInfo("Europe/Paris")
_HOURS = (9, 10, 11, 14, 15, 16)
_BATCH = 2000


def _load_appointments(
    clinician: ClinicianProfileRecord,
    kind: AppointmentTypeRecord,
    room_id: Any,
    patients: list[uuid.UUID],
    taken: set[tuple[uuid.UUID, datetime]],
    rng: random.Random,
    now: datetime,
) -> list[AppointmentRecord]:
    today = now.astimezone(LOAD_TIME_ZONE).date()
    starts = [
        datetime.combine(today + timedelta(days=day), time(hour), tzinfo=LOAD_TIME_ZONE)
        for day in range(-35, 36)
        if (today + timedelta(days=day)).isoweekday() <= 5
        for hour in _HOURS
    ]
    rows = []
    for start in sorted(rng.sample(starts, LOAD_APPOINTMENTS_PER_CLINICIAN)):
        past = start < now
        status = rng.choice(
            ("COMPLETED",) * 8 + ("CANCELLED", "NO_SHOW") if past else ("BOOKED", "CONFIRMED")
        )
        patient = rng.choice(patients)
        while (patient, start) in taken:
            patient = rng.choice(patients)
        taken.add((patient, start))
        rows.append(
            AppointmentRecord(
                patient_id=patient,
                clinician=clinician,
                appointment_type=kind,
                room_id=room_id,
                start=start,
                end=start + timedelta(minutes=kind.duration_minutes),
                status=status,
                source=rng.choice(("ONLINE", "ONLINE", "STAFF")),
            )
        )
    return rows


def seed_load(app: Container) -> None:
    """Load volume with no room, clinician or patient overlap; skipped when already there."""
    # To reseed a load set, empty the database: `docker compose down -v`, then `up` again.
    if AppointmentRecord.objects.filter(clinician__department__code__startswith="LOAD-").exists():
        return
    now = datetime.now(UTC)
    stamp = {"created_at": now, "updated_at": now}
    rng = random.Random(2026)  # noqa: S311
    specialties = {
        code: SpecialtyRecord.objects.get_or_create(
            code=code, defaults={"name": code.title(), "active": True, **stamp}
        )[0]
        for code in LOAD_SPECIALTIES
    }
    departments: list[DepartmentRecord] = []
    for number in range(1, LOAD_HOSPITALS + 1):
        hospital, _ = HospitalRecord.objects.get_or_create(
            code=f"LOAD-H{number:02}",
            defaults={
                "name": f"Hôpital de charge {number:02}",
                "street": f"{number} rue de la Charge",
                "postal_code": "59000",
                "city": "Lille",
                "country": "France",
                "phone": "+33 3 20 00 00 00",
                "time_zone": "Europe/Paris",
                "latitude": 43.0 + number * 0.7,
                "longitude": 1.0 + number * 0.5,
                "active": True,
                **stamp,
            },
        )
        for index in range(LOAD_DEPARTMENTS_PER_HOSPITAL):
            department, _ = DepartmentRecord.objects.get_or_create(
                code=f"LOAD-H{number:02}-D{index}",
                defaults={
                    "hospital": hospital,
                    "name": LOAD_SPECIALTIES[(number + index) % 5],
                    **stamp,
                },
            )
            AppointmentTypeRecord.objects.get_or_create(
                code=f"{department.code}-T",
                defaults={
                    "department": department,
                    "name": "Consultation",
                    "duration_minutes": 30,
                    "buffer_minutes": 5,
                    "colour": "#1D4E89",
                    "needs_room": True,
                    "bookable_online": True,
                    "active": True,
                    **stamp,
                },
            )
            departments.append(department)
    patients = [uuid.uuid4() for _ in range(LOAD_PATIENTS)]
    UserRecord.objects.bulk_create(
        (
            UserRecord(
                id=pid,
                email=f"load-patient-{n:05}@drlibre.localhost",
                full_name=f"Patient {n:05}",
                role="PATIENT",
                active=True,
                email_verified_at=now,
                **stamp,
            )
            for n, pid in enumerate(patients)
        ),
        batch_size=_BATCH,
    )
    appointments: list[AppointmentRecord] = []
    taken: set[tuple[uuid.UUID, datetime]] = set()
    today = now.astimezone(LOAD_TIME_ZONE).date()
    for n in range(LOAD_CLINICIANS):
        department = departments[n % len(departments)]
        user = UserRecord.objects.create(
            email=f"load-clinician-{n:03}@drlibre.localhost",
            full_name=f"Dr Charge {n:03}",
            role="CLINICIAN",
            active=True,
            email_verified_at=now,
            **stamp,
        )
        # One room per clinician of a department, so seeded appointments never share a room.
        room, _ = RoomRecord.objects.get_or_create(
            code=f"{department.code}-R{n // len(departments)}",
            defaults={
                "department": department,
                "name": "Consultation",
                "floor": "0",
                "capacity": 1,
                "equipment": [],
                "active": True,
                **stamp,
            },
        )
        profile = ClinicianProfileRecord.objects.create(
            user_id=user.id,
            department=department,
            specialty=specialties[department.name],
            title=f"Dr Charge {n:03}",
            bio="Praticien du jeu de charge.",
            default_room=room,
            weight=1 + n % 3,
            **stamp,
        )
        AvailabilityRuleModel.objects.bulk_create(
            AvailabilityRuleModel(
                clinician=profile,
                weekday=day,
                start=time(start),
                end=time(end),
                step_minutes=30,
                valid_from=today - timedelta(days=1),
            )
            for day in range(1, 6)
            for start, end in ((9, 12), (14, 17))
        )
        kind = AppointmentTypeRecord.objects.get(code=f"{department.code}-T")
        appointments += _load_appointments(profile, kind, room.id, patients, taken, rng, now)
    AppointmentRecord.objects.bulk_create(appointments, batch_size=_BATCH)
    app.extend_slot_horizon.execute()
    logger.info("seed_load_done", appointments=len(appointments), patients=len(patients))


# Each seeder gets or creates its rows, so the whole seed can run again safely.
SEEDERS: list[Callable[[Container], None]] = [
    seed_users,
    seed_referential,
    seed_clinician_profile,
    seed_availability,
    seed_passwordless_patient,
]


def main(size: str = "demo") -> None:
    app = container()
    with transaction.atomic():
        for seeder in SEEDERS:
            seeder(app)
        if size == "load":
            seed_load(app)
    logger.info("seed_done", seeders=len(SEEDERS))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the demo data, or the load volume on top.")
    parser.add_argument("--size", choices=("demo", "load"), default="demo")
    main(parser.parse_args().size)
