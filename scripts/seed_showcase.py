import os
import random
import unicodedata
import uuid
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

import structlog  # noqa: E402
from django.db import transaction  # noqa: E402
from django.db.models import QuerySet  # noqa: E402

from drlibre.booking.infrastructure.django.models import AppointmentRecord  # noqa: E402
from drlibre.bootstrap.container import Container, container  # noqa: E402
from drlibre.identity.infrastructure.django.models import UserRecord  # noqa: E402
from drlibre.organisation.infrastructure.django.models import (  # noqa: E402
    AppointmentTypeRecord,
    ClinicianProfileRecord,
)
from drlibre.scheduling.infrastructure.django.models import AvailabilityRuleModel  # noqa: E402
from scripts import seed  # noqa: E402
from scripts.seed import (  # noqa: E402
    CLINICIAN_EMAIL,
    DEMO_PASSWORD,
    SECOND_CLINICIAN_EMAIL,
    USERS,
    _by_code,
    _demo_admin,
    _upsert,
    _user_id,
)

logger = structlog.get_logger("drlibre.seed")

# Fictitious showcase volume on top of the demo seed: realistic names, one agenda per clinician.
HOSPITALS = (
    {
        "code": "HSUD",
        "name": "Hôpital Sud Confluence",
        "description": "Plateau chirurgical et consultations spécialisées.",
        "street": "12 quai des Mariniers",
        "postal_code": "69002",
        "city": "Lyon",
        "country": "France",
        "phone": "+33 4 72 00 00 00",
        "time_zone": "Europe/Paris",
        "latitude": "45.74",
        "longitude": "4.82",
    },
    {
        "code": "HOUEST",
        "name": "Centre hospitalier de l'Estuaire",
        "description": "Hôpital de proximité, mère-enfant et médecine générale.",
        "street": "5 boulevard de la Loire",
        "postal_code": "44000",
        "city": "Nantes",
        "country": "France",
        "phone": "+33 2 40 00 00 00",
        "time_zone": "Europe/Paris",
        "latitude": "47.21",
        "longitude": "-1.55",
    },
)
SPECIALTIES = (
    {"code": "DERMA", "name": "Dermatologie"},
    {"code": "NEURO", "name": "Neurologie"},
    {"code": "ORTHO", "name": "Orthopédie"},
    {"code": "OPHTA", "name": "Ophtalmologie"},
    {"code": "GYNECO", "name": "Gynécologie"},
    {"code": "GENE", "name": "Médecine générale"},
)
# Department code, name, hospital, specialty.
DEPARTMENTS = (
    ("HNORD-DERMA", "Dermatologie", "HNORD", "DERMA"),
    ("HNORD-NEURO", "Neurologie", "HNORD", "NEURO"),
    ("HSUD-ORTHO", "Orthopédie", "HSUD", "ORTHO"),
    ("HSUD-OPHTA", "Ophtalmologie", "HSUD", "OPHTA"),
    ("HSUD-CARD", "Cardiologie", "HSUD", "CARDIO"),
    ("HOUEST-GYNECO", "Gynécologie", "HOUEST", "GYNECO"),
    ("HOUEST-PEDIA", "Pédiatrie", "HOUEST", "PEDIA"),
    ("HOUEST-GENE", "Médecine générale", "HOUEST", "GENE"),
)
# Type code, name, department, duration, buffer, colour.
TYPES = (
    ("HNORD-DERMA-C", "Consultation de dermatologie", "HNORD-DERMA", 20, 5, "#AD1457"),
    ("HNORD-DERMA-N", "Contrôle des grains de beauté", "HNORD-DERMA", 30, 0, "#6A1B9A"),
    ("HNORD-NEURO-C", "Consultation de neurologie", "HNORD-NEURO", 45, 15, "#283593"),
    ("HSUD-ORTHO-C", "Consultation d'orthopédie", "HSUD-ORTHO", 20, 10, "#00695C"),
    ("HSUD-ORTHO-P", "Suivi post-opératoire", "HSUD-ORTHO", 15, 0, "#2E7D32"),
    ("HSUD-OPHTA-C", "Examen de la vue", "HSUD-OPHTA", 20, 0, "#0277BD"),
    ("HSUD-CARD-C", "Consultation de cardiologie", "HSUD-CARD", 30, 0, "#C62828"),
    ("HOUEST-GYNECO-C", "Consultation de gynécologie", "HOUEST-GYNECO", 30, 0, "#D84315"),
    ("HOUEST-GYNECO-S", "Suivi de grossesse", "HOUEST-GYNECO", 30, 15, "#EF6C00"),
    ("HOUEST-PEDIA-C", "Consultation pédiatrique", "HOUEST-PEDIA", 20, 10, "#558B2F"),
    ("HOUEST-GENE-C", "Consultation de médecine générale", "HOUEST-GENE", 15, 0, "#4E342E"),
)
# Weekly availability templates, weekday 0 is Sunday (spec §3.1).
SCHEDULES = {
    "full": tuple(
        (d, s, e) for d in range(1, 6) for s, e in (("09:00", "12:30"), ("14:00", "18:00"))
    ),
    "morning": tuple((d, "08:30", "12:30") for d in range(1, 6)),
    "part": tuple(
        (d, s, e) for d in (1, 2, 4) for s, e in (("09:00", "12:00"), ("13:30", "17:30"))
    ),
    "late": (*((d, "10:00", "19:00") for d in (2, 3, 4, 5)), (6, "09:00", "12:00")),
}
# Name, title, department, room floor, schedule, weight, bio.
CLINICIANS = (
    (
        "Sophie Lefebvre",
        "Dr",
        "HNORD-PEDIA",
        "2",
        "full",
        2,
        "Pédiatre, suivi du nourrisson et vaccinations.",
    ),
    ("Thomas Dubois", "Dr", "HNORD-DERMA", "1", "full", 1, "Dermatologue, dermatoses chroniques."),
    (
        "Yasmine Benali",
        "Dr",
        "HNORD-DERMA",
        "1",
        "part",
        1,
        "Dermatologue, dépistage des cancers cutanés.",
    ),
    (
        "Camille Moreau",
        "Pr",
        "HNORD-NEURO",
        "3",
        "morning",
        1,
        "Neurologue, migraines et épilepsie.",
    ),
    (
        "Julien Laurent",
        "Dr",
        "HSUD-ORTHO",
        "0",
        "full",
        2,
        "Chirurgien orthopédiste, genou et hanche.",
    ),
    (
        "Inès Garnier",
        "Dr",
        "HSUD-ORTHO",
        "0",
        "late",
        1,
        "Chirurgienne orthopédiste, main et poignet.",
    ),
    ("Nicolas Roux", "Dr", "HSUD-OPHTA", "1", "full", 1, "Ophtalmologue, cataracte et glaucome."),
    ("Léa Fontaine", "Dr", "HSUD-CARD", "2", "part", 1, "Cardiologue, rythmologie."),
    ("Émilie Mercier", "Dr", "HOUEST-GYNECO", "1", "full", 1, "Gynécologue-obstétricienne."),
    (
        "Karim Haddad",
        "Dr",
        "HOUEST-PEDIA",
        "1",
        "morning",
        1,
        "Pédiatre, allergologie de l'enfant.",
    ),
    ("Marion Chevalier", "Dr", "HOUEST-GENE", "0", "full", 2, "Médecin généraliste."),
    (
        "Lucas Girard",
        "Dr",
        "HOUEST-GENE",
        "0",
        "late",
        1,
        "Médecin généraliste, médecine du sport.",
    ),
    ("Mathilde Joseph", "Dr", "HATL-CARD", "0", "full", 1, "Cardiologue, hypertension artérielle."),
)
FIRST_NAMES = (
    "Jean",
    "Marie",
    "Pierre",
    "Nathalie",
    "Michel",
    "Isabelle",
    "Philippe",
    "Sylvie",
    "Alain",
    "Catherine",
    "Patrick",
    "Christine",
    "Laurent",
    "Valérie",
    "Olivier",
    "Sandrine",
    "Stéphane",
    "Céline",
    "Sébastien",
    "Aurélie",
    "Mehdi",
    "Fatima",
    "Kevin",
    "Julie",
    "Maxime",
    "Laura",
    "Romain",
    "Manon",
    "Hugo",
    "Chloé",
    "Louis",
    "Emma",
    "Gabriel",
    "Jade",
    "Adam",
    "Louise",
    "Raphaël",
    "Alice",
    "Arthur",
    "Lina",
    "Nadia",
    "Bruno",
    "Agnès",
    "Rémi",
    "Anaïs",
    "Samir",
)
LAST_NAMES = (
    "Martin",
    "Bernard",
    "Thomas",
    "Petit",
    "Robert",
    "Richard",
    "Durand",
    "Leroy",
    "Moreau",
    "Simon",
    "Michel",
    "Lefèvre",
    "Garcia",
    "David",
    "Bertrand",
    "Roux",
    "Vincent",
    "Fournier",
    "Morel",
    "Girard",
    "André",
    "Mercier",
    "Dupont",
    "Lambert",
    "Bonnet",
    "François",
    "Martinez",
    "Legrand",
    "Garnier",
    "Faure",
    "Rousseau",
    "Blanc",
    "Guérin",
    "Muller",
    "Henry",
    "Roussel",
    "Nicolas",
    "Perrin",
    "Morin",
    "Mathieu",
    "Clément",
    "Gauthier",
    "Dumont",
    "Lopez",
    "Fontaine",
    "Chevalier",
    "Robin",
    "Masson",
    "Sanchez",
    "Nguyen",
    "Benoit",
    "Diallo",
    "Lemaire",
    "Boyer",
)
REASONS = {
    "CARDIO": (
        "Essoufflement à l'effort",
        "Bilan avant reprise du sport",
        "Suivi d'hypertension",
        "Palpitations",
    ),
    "PEDIA": ("Vaccins", "Fièvre depuis deux jours", "Visite du 9e mois", "Toux persistante"),
    "DERMA": ("Eczéma", "Grain de beauté qui change", "Acné", "Démangeaisons"),
    "NEURO": ("Migraines fréquentes", "Fourmillements des mains", "Suivi d'épilepsie", "Vertiges"),
    "ORTHO": (
        "Douleur au genou",
        "Entorse de la cheville",
        "Contrôle après prothèse",
        "Mal de dos",
    ),
    "OPHTA": (
        "Baisse de la vision de près",
        "Renouvellement de lunettes",
        "Œil rouge",
        "Contrôle glaucome",
    ),
    "GYNECO": (
        "Suivi annuel",
        "Contraception",
        "Échographie du 2e trimestre",
        "Douleurs pelviennes",
    ),
    "GENE": ("Renouvellement d'ordonnance", "Certificat de sport", "Rhume", "Douleur à l'épaule"),
}
NOTES = (
    "Examen clinique sans particularité. Revoir dans six mois.",
    "Traitement adapté, contrôle à un mois.",
    "Bilan sanguin prescrit, résultats à apporter à la prochaine consultation.",
    "Amélioration nette depuis la dernière visite.",
    "Orientation vers un confrère pour avis complémentaire.",
)
# Specialty of every department a showcase clinician joins, demo ones included.
SPECIALTY_OF = {d[0]: d[3] for d in DEPARTMENTS} | {"HNORD-PEDIA": "PEDIA", "HATL-CARD": "CARDIO"}
PATIENTS = 600
PAST_DAYS = 42
FUTURE_DAYS = 21
PATIENT_DOMAIN = "patients.drlibre.localhost"
DEMO_PATIENT_EMAIL = USERS[3][2]
_TEMPORARY = "drlibre-temporary-2026"
_NAMESPACE = uuid.UUID("0b7d9f3e-4a62-4f1e-9c2d-5e8a1b3c7d90")
_STEP = 15


def _slug(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return ascii_text.lower().replace(" ", "-").replace("'", "")


def _seed_referential(app: Container) -> None:
    q = app.reference_queries
    actor = _demo_admin(app)
    hospitals = {
        h["code"]: _upsert(app.save_hospital, q.hospitals, h, actor=actor) for h in HOSPITALS
    }
    for code in ("HNORD", "HATL"):
        found = _by_code(q.hospitals, code)
        if found is not None:
            hospitals[code] = found
    for specialty in SPECIALTIES:
        _upsert(app.save_specialty, q.specialties, specialty, actor=actor)
    for code, name, hospital, _ in DEPARTMENTS:
        fields = {"code": code, "name": name, "hospital_id": str(hospitals[hospital])}
        _upsert(app.save_department, q.departments, fields, actor=actor)
    for code, name, department, duration, buffer, colour in TYPES:
        fields = {
            "code": code,
            "name": name,
            "department_id": str(_by_code(q.departments, department)),
            "duration_minutes": str(duration),
            "buffer_minutes": str(buffer),
            "colour": colour,
            "needs_room": "on",
            "bookable_online": "on",
        }
        _upsert(app.save_appointment_type, q.appointment_types, fields, actor=actor)


def _clinician_email(name: str) -> str:
    return f"{_slug(name).replace('-', '.')}@drlibre.localhost"


def _seed_clinicians(app: Container) -> None:
    q = app.reference_queries
    actor = _demo_admin(app)
    for n, (name, title, department, floor, schedule, weight, bio) in enumerate(CLINICIANS):
        email = _clinician_email(name)
        user = _user_id(app, email)
        if user is None:
            user = app.save_user.execute(
                actor=actor,
                user_id=None,
                full_name=name,
                email=email,
                role="CLINICIAN",
                active=True,
                temporary_password=_TEMPORARY,
            )
            app.change_password.execute(
                user_id=user, current_password=_TEMPORARY, new_password=DEMO_PASSWORD
            )
        if q.clinician_profile_of(user) is not None:
            continue
        room_code = f"{department}-{floor}{n:02}"
        room = _upsert(
            app.save_room,
            q.rooms,
            {
                "code": room_code,
                "name": f"Consultation {floor}{n:02}",
                "department_id": str(_by_code(q.departments, department)),
                "floor": floor,
                "capacity": "1",
                "equipment": "Table d'examen, Lavabo",
            },
            actor=actor,
        )
        specialty = SPECIALTY_OF[department]
        app.attach_clinician_profile.execute(
            actor=actor,
            user_id=str(user),
            fields={
                "department_id": str(_by_code(q.departments, department)),
                "specialty_id": str(_by_code(q.specialties, specialty)),
                "default_room_id": str(room),
                "title": title,
                "bio": bio,
                "weight": str(weight),
            },
        )
        for weekday, start, end in SCHEDULES[schedule]:
            app.save_availability_rule.execute(
                actor=user,
                rule_id=None,
                fields={
                    "weekday": str(weekday),
                    "start": start,
                    "end": end,
                    "step_minutes": str(_STEP),
                },
            )


def _seed_patients(rng: random.Random, now: datetime) -> list[UserRecord]:
    existing = list(UserRecord.objects.filter(email__endswith=f"@{PATIENT_DOMAIN}"))
    if existing:
        return existing
    rows, seen = [], set()
    while len(rows) < PATIENTS:
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        email = f"{_slug(first)}.{_slug(last)}@{PATIENT_DOMAIN}"
        if email in seen:
            email = f"{_slug(first)}.{_slug(last)}{len(rows)}@{PATIENT_DOMAIN}"
        seen.add(email)
        # About one patient in six is a child, booked in paediatrics only.
        age = rng.randint(1, 15) if rng.random() < 0.17 else rng.randint(18, 88)
        rows.append(
            UserRecord(
                id=uuid.uuid5(_NAMESPACE, email),
                email=email,
                full_name=f"{first} {last}",
                role="PATIENT",
                active=True,
                phone="+33 6 " + " ".join(str(rng.randint(10, 99)) for _ in range(4)),
                birth_date=now.date() - timedelta(days=age * 365 + rng.randint(0, 364)),
                email_verified_at=now,
                created_at=now - timedelta(days=rng.randint(30, 400)),
                updated_at=now,
            )
        )
    UserRecord.objects.bulk_create(rows, ignore_conflicts=True)
    return rows


def _is_child(patient: UserRecord, now: datetime) -> bool:
    return patient.birth_date is not None and patient.birth_date.year > now.year - 16


def _status(start: datetime, now: datetime, rng: random.Random) -> str:
    if start >= now:
        return "CANCELLED" if rng.random() < 0.06 else "BOOKED"
    if start > now - timedelta(minutes=45):
        return "CHECKED_IN"
    roll = rng.random()
    return "NO_SHOW" if roll < 0.06 else "CANCELLED" if roll < 0.17 else "COMPLETED"


def _occupancy(day: date, today: date) -> float:
    if day < today:
        return 0.78
    return 0.62 if (day - today).days <= 7 else 0.33


def _agenda(
    profile: ClinicianProfileRecord,
    types: list[AppointmentTypeRecord],
    patients: list[UserRecord],
    taken: set[tuple[uuid.UUID, date]],
    rng: random.Random,
    now: datetime,
) -> list[AppointmentRecord]:
    zone = ZoneInfo(profile.department.hospital.time_zone)
    today = now.astimezone(zone).date()
    specialty = profile.specialty.code
    children = specialty == "PEDIA"
    pool = [
        p
        for p in patients
        if (p.birth_date is not None and p.birth_date.year > now.year - 16) == children
    ]
    rules = list(AvailabilityRuleModel.objects.filter(clinician=profile))
    rows = []
    for offset in range(-PAST_DAYS, FUTURE_DAYS + 1):
        day = today + timedelta(days=offset)
        weekday = (day.weekday() + 1) % 7
        for rule in (r for r in rules if r.weekday == weekday):
            cursor = datetime.combine(day, rule.start, tzinfo=zone)
            close = datetime.combine(day, rule.end, tzinfo=zone)
            while True:
                kind = rng.choice(types)
                end = cursor + timedelta(minutes=kind.duration_minutes)
                if end > close:
                    break
                block = -(-(kind.duration_minutes + kind.buffer_minutes) // _STEP) * _STEP
                if rng.random() < _occupancy(day, today):
                    patient = rng.choice(pool)
                    if (patient.id, day) not in taken:
                        taken.add((patient.id, day))
                        rows.append(
                            _appointment(profile, kind, patient, cursor, end, rng, now, specialty)
                        )
                cursor += timedelta(minutes=block)
    return rows


def _appointment(
    profile: ClinicianProfileRecord,
    kind: AppointmentTypeRecord,
    patient: UserRecord,
    start: datetime,
    end: datetime,
    rng: random.Random,
    now: datetime,
    specialty: str,
) -> AppointmentRecord:
    status = _status(start, now, rng)
    cancelled = status == "CANCELLED"
    source = rng.choices(("ONLINE", "ROUND_ROBIN", "STAFF"), weights=(55, 15, 30))[0]
    booked = start - timedelta(days=rng.randint(1, 30))
    return AppointmentRecord(
        id=uuid.uuid5(_NAMESPACE, f"{profile.id}/{start.isoformat()}"),
        patient_id=patient.id,
        clinician=profile,
        appointment_type=kind,
        room_id=profile.default_room_id,
        start=start,
        end=end,
        status=status,
        source=source,
        reason=rng.choice(REASONS.get(specialty, REASONS["GENE"])),
        cancelled_at=min(start - timedelta(hours=rng.randint(26, 96)), now) if cancelled else None,
        cancellation_reason=rng.choice(("Empêchement", "Rendez-vous déplacé", "Malade"))
        if cancelled
        else None,
        clinical_notes=rng.choice(NOTES) if status == "COMPLETED" and rng.random() < 0.6 else None,
        created_at=min(booked, now),
        updated_at=now,
    )


# The demo patient's upcoming visits, so the portal shows more than past rows.
DEMO_PATIENT_VISITS = (("HNORD-DERMA-C", 4, 10), ("HSUD-OPHTA-C", 11, 15))


def _demo_patient_agenda(
    profiles: "QuerySet[ClinicianProfileRecord]",
    rng: random.Random,
    now: datetime,
    taken: set[tuple[uuid.UUID, date]],
) -> list[AppointmentRecord]:
    patient = UserRecord.objects.filter(email=DEMO_PATIENT_EMAIL).first()
    rows = []
    for code, ahead, hour in DEMO_PATIENT_VISITS:
        kind = AppointmentTypeRecord.objects.filter(code=code).first()
        profile = profiles.filter(department_id=kind.department_id).first() if kind else None
        if patient is None or kind is None or profile is None:
            continue
        day = now.astimezone(ZoneInfo("Europe/Paris")).date() + timedelta(days=ahead)
        while day.weekday() >= 5:
            day += timedelta(days=1)
        start = datetime.combine(
            day, datetime.min.time().replace(hour=hour), tzinfo=ZoneInfo("Europe/Paris")
        )
        taken.add((patient.id, day))
        row = _appointment(
            profile,
            kind,
            patient,
            start,
            start + timedelta(minutes=kind.duration_minutes),
            rng,
            now,
            profile.specialty.code,
        )
        row.status, row.source, row.cancelled_at, row.cancellation_reason = (
            "BOOKED",
            "ONLINE",
            None,
            None,
        )
        rows.append(row)
    return rows


def seed_showcase(app: Container) -> None:
    """Realistic demo volume: 3 more hospitals' worth of agendas; appointments once."""
    _seed_referential(app)
    _seed_clinicians(app)
    now = datetime.now(UTC)
    rng = random.Random(2026)  # noqa: S311  # nosec B311
    patients = _seed_patients(rng, now)
    showcase = {_clinician_email(c[0]) for c in CLINICIANS} | {
        CLINICIAN_EMAIL,
        SECOND_CLINICIAN_EMAIL,
    }
    users = UserRecord.objects.filter(email__in=showcase).values_list("id", flat=True)
    profiles = ClinicianProfileRecord.objects.filter(user_id__in=users).select_related(
        "department__hospital", "specialty"
    )
    if AppointmentRecord.objects.filter(patient_id__in=[p.id for p in patients]).exists():
        logger.info("seed_showcase_skipped")
        return
    taken: set[tuple[uuid.UUID, date]] = set()
    rows = _demo_patient_agenda(profiles, rng, now, taken)
    for profile in profiles.order_by("created_at"):
        types = list(
            AppointmentTypeRecord.objects.filter(
                department=profile.department, active=True, bookable_online=True
            )
        )
        if types:
            rows += _agenda(profile, types, patients, taken, rng, now)
    # A clash with an existing demo row keeps that row (exclusion constraints).
    AppointmentRecord.objects.bulk_create(rows, batch_size=2000, ignore_conflicts=True)
    app.extend_slot_horizon.execute()
    logger.info("seed_showcase_done", appointments=len(rows), patients=len(patients))


def main() -> None:
    seed.main()
    with transaction.atomic():
        seed_showcase(container())


if __name__ == "__main__":
    main()
