from datetime import UTC, datetime

from drlibre.bootstrap.container import Adapters, Container, wire
from tests.fakes.audit_actors import InMemoryAuditActors
from tests.fakes.audit_log import InMemoryAuditLog
from tests.fakes.clock import FixedClock
from tests.fakes.database_probe import InMemoryDatabaseProbe
from tests.fakes.failed_sign_ins import InMemoryFailedSignIns
from tests.fakes.in_memory_mailer import InMemoryMailer
from tests.fakes.organisation import (
    InMemoryAppointmentTypes,
    InMemoryClinicianProfiles,
    InMemoryDepartments,
    InMemoryHospitals,
    InMemoryReferenceQueries,
    InMemoryRooms,
    InMemoryScheduleDependents,
    InMemorySpecialties,
)
from tests.fakes.password_hasher import InMemoryPasswordHasher
from tests.fakes.scheduling import (
    FixedSchedulingDirectory,
    InMemoryActiveAppointments,
    InMemoryAvailabilityRules,
    InMemorySlotStore,
    InMemoryTimeOffs,
)
from tests.fakes.sessions import InMemorySessions
from tests.fakes.staff_directory import InMemoryStaffDirectory
from tests.fakes.staff_profiles import InMemoryStaffProfiles
from tests.fakes.tokens import InMemoryTokenGenerator
from tests.fakes.unit_of_work import InMemoryUnitOfWork
from tests.fakes.upcoming_appointments import InMemoryUpcomingAppointments
from tests.fakes.user_queries import InMemoryUserQueries
from tests.fakes.users import InMemoryUsers


class FakeWorld:
    """Every fake adapter, wired through the real composition root."""

    def __init__(self) -> None:
        self.clock = FixedClock(datetime(2026, 11, 20, 10, tzinfo=UTC))
        self.database = InMemoryDatabaseProbe()
        self.mailer = InMemoryMailer()
        self.audit = InMemoryAuditLog()
        self.users = InMemoryUsers()
        self.sessions = InMemorySessions()
        self.hasher = InMemoryPasswordHasher()
        self.failures = InMemoryFailedSignIns()
        self.tokens = InMemoryTokenGenerator()
        self.hospitals = InMemoryHospitals()
        self.specialties = InMemorySpecialties()
        self.departments = InMemoryDepartments()
        self.rooms = InMemoryRooms()
        self.appointment_types = InMemoryAppointmentTypes()
        self.schedule = InMemoryScheduleDependents()
        self.profiles = InMemoryClinicianProfiles()
        self.appointments = InMemoryUpcomingAppointments()
        self.actors = InMemoryAuditActors(self.audit)
        self.user_queries = InMemoryUserQueries(self.users)
        self.staff = InMemoryStaffDirectory()
        self.staff_profiles = InMemoryStaffProfiles()
        self.scheduling_directory = FixedSchedulingDirectory()
        self.availability_rules = InMemoryAvailabilityRules()
        self.time_offs = InMemoryTimeOffs()
        self.active_appointments = InMemoryActiveAppointments()
        self.slots = InMemorySlotStore()
        self.uow = InMemoryUnitOfWork(
            self.audit,
            self.users,
            self.sessions,
            self.hospitals,
            self.specialties,
            self.departments,
            self.rooms,
            self.appointment_types,
            self.profiles,
            self.availability_rules,
            self.time_offs,
            self.slots,
        )
        self.app: Container = wire(self.adapters())

    def adapters(self) -> Adapters:
        return Adapters(
            clock=self.clock,
            database=self.database,
            mailer=self.mailer,
            uow=self.uow,
            audit=self.audit,
            users=self.users,
            sessions=self.sessions,
            hasher=self.hasher,
            failures=self.failures,
            tokens=self.tokens,
            hospitals=self.hospitals,
            specialties=self.specialties,
            departments=self.departments,
            rooms=self.rooms,
            appointment_types=self.appointment_types,
            schedule=self.schedule,
            reference_queries=InMemoryReferenceQueries(
                hospitals=self.hospitals,
                specialties=self.specialties,
                departments=self.departments,
                rooms=self.rooms,
                appointment_types=self.appointment_types,
                profiles=self.profiles,
            ),
            appointments=self.appointments,
            actors=self.actors,
            user_queries=self.user_queries,
            staff_lookup=self.user_queries,
            profiles=self.profiles,
            staff=self.staff,
            staff_profiles=self.staff_profiles,
        )
