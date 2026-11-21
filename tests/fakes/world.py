from datetime import UTC, datetime

from drlibre.booking.application.use_cases.open_holds import OpenHoldsUseCase
from drlibre.booking.infrastructure.outbox_notices import OutboxBookingNotices
from drlibre.bootstrap.container import Adapters, BookingAdapters, Container, wire
from drlibre.identity.infrastructure.outbox_link_notices import OutboxLinkNotices
from drlibre.notifications.application.use_cases.notify import NotifyUseCase
from drlibre.notifications.application.use_cases.reminded_appointments import (
    RemindedAppointmentsUseCase,
)
from drlibre.search.infrastructure.sql_queries import SqlSearchQueries
from tests.fakes.appointment_history import InMemoryAppointmentHistory
from tests.fakes.audit_actors import InMemoryAuditActors
from tests.fakes.audit_log import InMemoryAuditLog
from tests.fakes.audit_queries import InMemoryAuditQueries
from tests.fakes.booking import (
    FixedBookingDirectory,
    FixedCodeIssuer,
    InMemoryAdminAppointments,
    InMemoryAppointmentQueries,
    InMemoryAppointments,
    InMemoryFreeSlots,
    InMemoryHolds,
    InMemoryPatientAgenda,
    InMemoryPatients,
    InMemoryRoundRobinLedger,
    InMemoryStaff,
    InMemoryVerificationCodes,
    InMemoryWaitlist,
    InMemoryWaitlistQueries,
    RecordingScheduleLocks,
    RecordingSlotRefresh,
)
from tests.fakes.clinician_agenda import InMemoryClinicianAgenda
from tests.fakes.clock import FixedClock
from tests.fakes.database_probe import InMemoryDatabaseProbe
from tests.fakes.email_outbox import RecordingEmailOutbox
from tests.fakes.failed_sign_ins import InMemoryFailedSignIns
from tests.fakes.in_memory_mailer import InMemoryMailer
from tests.fakes.notifications import InMemoryNotifications
from tests.fakes.organisation import (
    InMemoryAppointmentTypes,
    InMemoryClinicianProfiles,
    InMemoryDepartments,
    InMemoryHospitals,
    InMemoryReferenceQueries,
    InMemoryRooms,
    InMemoryScheduleDependents,
    InMemorySlotRefresh,
    InMemorySpecialties,
)
from tests.fakes.password_hasher import InMemoryPasswordHasher
from tests.fakes.rate_limiter import InMemoryRateLimiter
from tests.fakes.reporting import InMemoryActivityQueries, InMemoryAdmins
from tests.fakes.scheduling import (
    FixedSchedulingDirectory,
    InMemoryAvailabilityQueries,
    InMemoryAvailabilityRules,
    InMemoryClinicianAppointments,
    InMemorySlotHolds,
    InMemorySlotStore,
    InMemoryTimeOffs,
)
from tests.fakes.sessions import InMemorySessions
from tests.fakes.sign_in_links import InMemorySignInLinks
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
        self.links = InMemorySignInLinks()
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
        self.clinician_appointments = InMemoryClinicianAppointments()
        self.slots = InMemorySlotStore()
        self.slot_holds = InMemorySlotHolds()
        self.slot_refresh = InMemorySlotRefresh()
        self.availability_queries = InMemoryAvailabilityQueries(
            rules=self.availability_rules, time_offs=self.time_offs
        )
        self.booking_appointments = InMemoryAppointments()
        self.waitlist = InMemoryWaitlist(self.booking_appointments)
        self.waitlist_queries = InMemoryWaitlistQueries(self.waitlist, self.users)
        self.admin_appointments = InMemoryAdminAppointments(self.booking_appointments, self.users)
        self.audit_queries = InMemoryAuditQueries(self.audit)
        self.booking_queries = InMemoryAppointmentQueries(self.booking_appointments, self.waitlist)
        self.agenda = InMemoryPatientAgenda(self.booking_appointments)
        self.booking_directory = FixedBookingDirectory()
        self.holds = InMemoryHolds()
        self.codes = InMemoryVerificationCodes()
        self.issuer = FixedCodeIssuer()
        self.limiter = InMemoryRateLimiter(self.clock)
        self.outbox = RecordingEmailOutbox()
        self.free_slots = InMemoryFreeSlots(self.holds, self.clock)
        self.booking_slot_refresh = RecordingSlotRefresh()
        self.schedule_locks = RecordingScheduleLocks()
        self.patients = InMemoryPatients(self.users)
        self.activity = InMemoryActivityQueries()
        self.clinician_agenda = InMemoryClinicianAgenda(
            appointments=self.booking_appointments,
            users=self.users,
            directory=self.booking_directory,
            slots=self.slots,
            holds=self.holds,
        )
        self.notifications = InMemoryNotifications()
        self.notify = NotifyUseCase(clock=self.clock, notifications=self.notifications)
        self.notices = OutboxBookingNotices(
            outbox=self.outbox,
            notify=self.notify,
            reminded=RemindedAppointmentsUseCase(notifications=self.notifications),
            directory=self.booking_directory,
            patients=self.patients,
            public_base_url="http://localhost:8000",
        )
        self.ledger = InMemoryRoundRobinLedger()
        self.uow = InMemoryUnitOfWork(
            self.audit,
            self.users,
            self.sessions,
            self.links,
            self.hospitals,
            self.specialties,
            self.departments,
            self.rooms,
            self.appointment_types,
            self.profiles,
            self.availability_rules,
            self.time_offs,
            self.slots,
            self.slot_refresh,
            self.booking_appointments,
            self.booking_slot_refresh,
            self.holds,
            self.codes,
            self.outbox,
            self.ledger,
            self.notifications,
            self.waitlist,
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
            audit_queries=self.audit_queries,
            user_queries=self.user_queries,
            staff_lookup=self.user_queries,
            patient_lookup=self.user_queries,
            profiles=self.profiles,
            staff=self.staff,
            staff_profiles=self.staff_profiles,
            scheduling_directory=self.scheduling_directory,
            availability_rules=self.availability_rules,
            time_offs=self.time_offs,
            clinician_appointments=self.clinician_appointments,
            slot_store=self.slots,
            slot_queries=self.slots,
            slot_holds=self.slot_holds,
            availability_queries=self.availability_queries,
            slot_refresh=self.slot_refresh,
            booking=BookingAdapters(
                appointments=self.booking_appointments,
                directory=self.booking_directory,
                free_slots=self.free_slots,
                slot_refresh=self.booking_slot_refresh,
                locks=self.schedule_locks,
                patients=self.patients,
                notices=self.notices,
                ledger=self.ledger,
                holds=self.holds,
                open_holds=OpenHoldsUseCase(holds=self.holds),
                codes=self.codes,
                issuer=self.issuer,
                limiter=self.limiter,
                agenda=self.agenda,
                clinician_agenda=self.clinician_agenda,
                history=InMemoryAppointmentHistory(self.audit),
                waitlist=self.waitlist,
                waitlist_queries=self.waitlist_queries,
                staff=InMemoryStaff(self.users),
                admin_appointments=self.admin_appointments,
            ),
            links=self.links,
            link_notices=OutboxLinkNotices(
                outbox=self.outbox, public_base_url="http://localhost:8000"
            ),
            # Search is a read side tested on PostgreSQL: the real adapter, never reached by fakes.
            search_queries=SqlSearchQueries(),
            activity_queries=self.activity,
            admins=InMemoryAdmins(self.users),
            notifications=self.notifications,
            notify=self.notify,
            time_zone="Europe/Paris",
        )
