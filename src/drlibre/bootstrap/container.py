from dataclasses import dataclass

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.audit.infrastructure.queries import DjangoAuditQueries
from drlibre.audit.infrastructure.unit_of_work import DjangoUnitOfWork
from drlibre.booking.application.ports.inbound import BookAppointment
from drlibre.booking.application.ports.outbound import (
    Appointments as BookingAppointments,
)
from drlibre.booking.application.ports.outbound import (
    BookingDirectory,
    BookingNotices,
    FreeSlots,
    Patients,
    RoundRobinLedger,
    ScheduleLocks,
)
from drlibre.booking.application.ports.outbound import SlotRefresh as BookingSlotRefresh
from drlibre.booking.application.use_cases.book_appointment import BookAppointmentUseCase
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.infrastructure.unwired import UnwiredBookAppointment
from drlibre.health.application.ports.inbound import CheckHealth
from drlibre.health.application.ports.outbound import DatabaseProbe
from drlibre.health.application.use_cases.check_health import CheckHealthUseCase
from drlibre.health.infrastructure.database_probe import DjangoDatabaseProbe
from drlibre.identity.application.ports.inbound import (
    AuthenticateSession,
    ChangePassword,
    DeleteUser,
    SaveUser,
    SignIn,
    SignOut,
    StaffLookup,
    UserQueries,
)
from drlibre.identity.application.ports.outbound import (
    AuditActors,
    FailedSignIns,
    PasswordHasher,
    Sessions,
    StaffProfiles,
    TokenGenerator,
    UpcomingAppointments,
    Users,
)
from drlibre.identity.application.use_cases.authenticate_session import (
    AuthenticateSessionUseCase,
)
from drlibre.identity.application.use_cases.change_password import ChangePasswordUseCase
from drlibre.identity.application.use_cases.delete_user import DeleteUserUseCase
from drlibre.identity.application.use_cases.save_user import SaveUserUseCase
from drlibre.identity.application.use_cases.sign_in import SignInUseCase
from drlibre.identity.application.use_cases.sign_out import SignOutUseCase
from drlibre.identity.infrastructure.audit_actors import AuditLogActors
from drlibre.identity.infrastructure.failed_sign_ins import RedisFailedSignIns
from drlibre.identity.infrastructure.password_hasher import DjangoPasswordHasher
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.identity.infrastructure.repositories import DjangoSessions, DjangoUsers
from drlibre.identity.infrastructure.staff_profiles import OrganisationStaffProfiles
from drlibre.identity.infrastructure.tokens import SecretsTokenGenerator
from drlibre.identity.infrastructure.upcoming_appointments import NoAppointmentsYet
from drlibre.notifications.application.ports.outbound import Mailer
from drlibre.notifications.infrastructure.smtp_mailer import SmtpMailer
from drlibre.organisation.application.ports.inbound import (
    AttachClinicianProfile,
    DeleteAppointmentType,
    DeleteClinicianProfile,
    DeleteDepartment,
    DeleteHospital,
    DeleteRoom,
    DeleteSpecialty,
    EditClinicianProfile,
    ReferenceQueries,
    SaveAppointmentType,
    SaveDepartment,
    SaveHospital,
    SaveRoom,
    SaveSpecialty,
)
from drlibre.organisation.application.ports.outbound import (
    AppointmentTypes,
    ClinicianProfiles,
    Departments,
    Hospitals,
    Rooms,
    ScheduleDependents,
    SlotRefresh,
    Specialties,
    StaffDirectory,
)
from drlibre.organisation.application.use_cases.attach_clinician_profile import (
    AttachClinicianProfileUseCase,
)
from drlibre.organisation.application.use_cases.delete_appointment_type import (
    DeleteAppointmentTypeUseCase,
)
from drlibre.organisation.application.use_cases.delete_clinician_profile import (
    DeleteClinicianProfileUseCase,
)
from drlibre.organisation.application.use_cases.delete_department import DeleteDepartmentUseCase
from drlibre.organisation.application.use_cases.delete_hospital import DeleteHospitalUseCase
from drlibre.organisation.application.use_cases.delete_room import DeleteRoomUseCase
from drlibre.organisation.application.use_cases.delete_specialty import DeleteSpecialtyUseCase
from drlibre.organisation.application.use_cases.edit_clinician_profile import (
    EditClinicianProfileUseCase,
)
from drlibre.organisation.application.use_cases.save_appointment_type import (
    SaveAppointmentTypeUseCase,
)
from drlibre.organisation.application.use_cases.save_department import SaveDepartmentUseCase
from drlibre.organisation.application.use_cases.save_hospital import SaveHospitalUseCase
from drlibre.organisation.application.use_cases.save_room import SaveRoomUseCase
from drlibre.organisation.application.use_cases.save_specialty import SaveSpecialtyUseCase
from drlibre.organisation.infrastructure.queries import DjangoReferenceQueries
from drlibre.organisation.infrastructure.repositories import (
    DjangoAppointmentTypes,
    DjangoClinicianProfiles,
    DjangoDepartments,
    DjangoHospitals,
    DjangoRooms,
    DjangoSpecialties,
)
from drlibre.organisation.infrastructure.schedule_dependents import SchedulingScheduleDependents
from drlibre.organisation.infrastructure.slot_refresh import SchedulingSlotRefresh
from drlibre.organisation.infrastructure.staff_directory import IdentityStaffDirectory
from drlibre.scheduling.application.ports.inbound import (
    AvailabilityQueries,
    DeleteAvailabilityRule,
    DeleteTimeOff,
    ExtendSlotHorizon,
    FindFreeSlots,
    RecordTimeOff,
    SaveAvailabilityRule,
)
from drlibre.scheduling.application.ports.outbound import (
    AvailabilityRules,
    ClinicianAppointments,
    SchedulingDirectory,
    SlotQueries,
    SlotStore,
    TimeOffs,
)
from drlibre.scheduling.application.use_cases.delete_availability_rule import (
    DeleteAvailabilityRuleUseCase,
)
from drlibre.scheduling.application.use_cases.delete_time_off import DeleteTimeOffUseCase
from drlibre.scheduling.application.use_cases.extend_slot_horizon import ExtendSlotHorizonUseCase
from drlibre.scheduling.application.use_cases.find_free_slots import FindFreeSlotsUseCase
from drlibre.scheduling.application.use_cases.record_time_off import RecordTimeOffUseCase
from drlibre.scheduling.application.use_cases.refresh_slots import RefreshSlotsUseCase
from drlibre.scheduling.application.use_cases.save_availability_rule import (
    SaveAvailabilityRuleUseCase,
)
from drlibre.scheduling.infrastructure.directory import OrganisationSchedulingDirectory
from drlibre.scheduling.infrastructure.no_appointments_yet import (
    NoAppointmentsYet as NoClinicianAppointmentsYet,
)
from drlibre.scheduling.infrastructure.queries import DjangoAvailabilityQueries
from drlibre.scheduling.infrastructure.repositories import (
    DjangoAvailabilityRules,
    DjangoTimeOffs,
)
from drlibre.scheduling.infrastructure.slot_queries import DjangoSlotQueries
from drlibre.scheduling.infrastructure.slot_store import DjangoSlotStore
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.system_clock import SystemClock
from drlibre.shared_kernel.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class BookingAdapters:
    """Outbound adapters of the booking context."""

    appointments: BookingAppointments
    directory: BookingDirectory
    free_slots: FreeSlots
    slot_refresh: BookingSlotRefresh
    locks: ScheduleLocks
    patients: Patients
    notices: BookingNotices
    ledger: RoundRobinLedger


@dataclass(frozen=True, slots=True)
class Adapters:
    """Every outbound adapter; tests pass in-memory fakes in their place."""

    clock: Clock
    database: DatabaseProbe
    mailer: Mailer
    uow: UnitOfWork
    audit: AuditLog
    users: Users
    sessions: Sessions
    hasher: PasswordHasher
    failures: FailedSignIns
    tokens: TokenGenerator
    hospitals: Hospitals
    specialties: Specialties
    departments: Departments
    rooms: Rooms
    appointment_types: AppointmentTypes
    schedule: ScheduleDependents
    reference_queries: ReferenceQueries
    appointments: UpcomingAppointments
    actors: AuditActors
    user_queries: UserQueries
    staff_lookup: StaffLookup
    profiles: ClinicianProfiles
    staff: StaffDirectory
    staff_profiles: StaffProfiles
    scheduling_directory: SchedulingDirectory
    availability_rules: AvailabilityRules
    time_offs: TimeOffs
    clinician_appointments: ClinicianAppointments
    slot_store: SlotStore
    slot_queries: SlotQueries
    availability_queries: AvailabilityQueries
    # None wires organisation to scheduling's own RefreshSlots.
    slot_refresh: SlotRefresh | None = None
    # None until the Django booking adapters exist (E3 phase 3).
    booking: BookingAdapters | None = None


@dataclass(frozen=True, slots=True)
class Container:
    clock: Clock
    check_health: CheckHealth
    mailer: Mailer
    sign_in: SignIn
    sign_out: SignOut
    authenticate_session: AuthenticateSession
    change_password: ChangePassword
    save_hospital: SaveHospital
    delete_hospital: DeleteHospital
    save_specialty: SaveSpecialty
    delete_specialty: DeleteSpecialty
    save_department: SaveDepartment
    delete_department: DeleteDepartment
    save_room: SaveRoom
    delete_room: DeleteRoom
    save_appointment_type: SaveAppointmentType
    delete_appointment_type: DeleteAppointmentType
    reference_queries: ReferenceQueries
    save_user: SaveUser
    delete_user: DeleteUser
    user_queries: UserQueries
    staff_lookup: StaffLookup
    attach_clinician_profile: AttachClinicianProfile
    edit_clinician_profile: EditClinicianProfile
    delete_clinician_profile: DeleteClinicianProfile
    save_availability_rule: SaveAvailabilityRule
    delete_availability_rule: DeleteAvailabilityRule
    record_time_off: RecordTimeOff
    delete_time_off: DeleteTimeOff
    availability_queries: AvailabilityQueries
    extend_slot_horizon: ExtendSlotHorizon
    find_free_slots: FindFreeSlots
    book_appointment: BookAppointment


def wire(a: Adapters) -> Container:
    clock, uow, audit = a.clock, a.uow, a.audit
    directory = a.scheduling_directory
    refresh = RefreshSlotsUseCase(
        clock=clock,
        directory=directory,
        rules=a.availability_rules,
        time_offs=a.time_offs,
        appointments=a.clinician_appointments,
        store=a.slot_store,
    )
    slots = a.slot_refresh or SchedulingSlotRefresh(refresh=refresh)
    book_appointment = _wire_booking(a)
    return Container(
        clock=clock,
        check_health=CheckHealthUseCase(clock=clock, database=a.database),
        mailer=a.mailer,
        sign_in=SignInUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            users=a.users,
            sessions=a.sessions,
            hasher=a.hasher,
            failures=a.failures,
            tokens=a.tokens,
        ),
        sign_out=SignOutUseCase(clock=clock, uow=uow, audit=audit, sessions=a.sessions),
        authenticate_session=AuthenticateSessionUseCase(
            clock=clock, users=a.users, sessions=a.sessions
        ),
        change_password=ChangePasswordUseCase(
            clock=clock, uow=uow, audit=audit, users=a.users, hasher=a.hasher
        ),
        save_hospital=SaveHospitalUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            hospitals=a.hospitals,
            departments=a.departments,
            profiles=a.profiles,
            slots=slots,
        ),
        delete_hospital=DeleteHospitalUseCase(
            clock=clock, uow=uow, audit=audit, hospitals=a.hospitals, departments=a.departments
        ),
        save_specialty=SaveSpecialtyUseCase(
            clock=clock, uow=uow, audit=audit, specialties=a.specialties
        ),
        delete_specialty=DeleteSpecialtyUseCase(
            clock=clock, uow=uow, audit=audit, specialties=a.specialties, profiles=a.profiles
        ),
        save_department=SaveDepartmentUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            departments=a.departments,
            hospitals=a.hospitals,
            profiles=a.profiles,
            slots=slots,
        ),
        delete_department=DeleteDepartmentUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            departments=a.departments,
            rooms=a.rooms,
            appointment_types=a.appointment_types,
            profiles=a.profiles,
        ),
        save_room=SaveRoomUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            rooms=a.rooms,
            departments=a.departments,
            profiles=a.profiles,
        ),
        delete_room=DeleteRoomUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            rooms=a.rooms,
            schedule=a.schedule,
            profiles=a.profiles,
        ),
        save_appointment_type=SaveAppointmentTypeUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            appointment_types=a.appointment_types,
            departments=a.departments,
            profiles=a.profiles,
            slots=slots,
        ),
        delete_appointment_type=DeleteAppointmentTypeUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            appointment_types=a.appointment_types,
            schedule=a.schedule,
        ),
        reference_queries=a.reference_queries,
        save_user=SaveUserUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            users=a.users,
            sessions=a.sessions,
            hasher=a.hasher,
            appointments=a.appointments,
            profiles=a.staff_profiles,
        ),
        delete_user=DeleteUserUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            users=a.users,
            sessions=a.sessions,
            appointments=a.appointments,
            actors=a.actors,
            profiles=a.staff_profiles,
        ),
        user_queries=a.user_queries,
        staff_lookup=a.staff_lookup,
        attach_clinician_profile=AttachClinicianProfileUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            slots=slots,
            profiles=a.profiles,
            staff=a.staff,
            departments=a.departments,
            specialties=a.specialties,
            rooms=a.rooms,
        ),
        edit_clinician_profile=EditClinicianProfileUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            slots=slots,
            profiles=a.profiles,
            departments=a.departments,
            specialties=a.specialties,
            rooms=a.rooms,
        ),
        delete_clinician_profile=DeleteClinicianProfileUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            slots=slots,
            profiles=a.profiles,
            schedule=a.schedule,
        ),
        save_availability_rule=SaveAvailabilityRuleUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            directory=directory,
            rules=a.availability_rules,
            refresh=refresh,
        ),
        delete_availability_rule=DeleteAvailabilityRuleUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            directory=directory,
            rules=a.availability_rules,
            refresh=refresh,
        ),
        record_time_off=RecordTimeOffUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            directory=directory,
            time_offs=a.time_offs,
            refresh=refresh,
        ),
        delete_time_off=DeleteTimeOffUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            directory=directory,
            time_offs=a.time_offs,
            refresh=refresh,
        ),
        availability_queries=a.availability_queries,
        extend_slot_horizon=ExtendSlotHorizonUseCase(
            uow=uow, rules=a.availability_rules, refresh=refresh
        ),
        find_free_slots=FindFreeSlotsUseCase(
            clock=clock, directory=directory, queries=a.slot_queries
        ),
        book_appointment=book_appointment,
    )


def _wire_booking(a: Adapters) -> BookAppointment:
    booking = a.booking
    if booking is None:
        return UnwiredBookAppointment()
    placement = Placement(
        clock=a.clock,
        uow=a.uow,
        audit=a.audit,
        directory=booking.directory,
        appointments=booking.appointments,
        free_slots=booking.free_slots,
        slot_refresh=booking.slot_refresh,
        locks=booking.locks,
        patients=booking.patients,
        notices=booking.notices,
    )
    return BookAppointmentUseCase(
        clock=a.clock,
        uow=a.uow,
        placement=placement,
        directory=booking.directory,
        free_slots=booking.free_slots,
        ledger=booking.ledger,
    )


def real_adapters() -> Adapters:
    user_queries = DjangoUserQueries()
    reference_queries = DjangoReferenceQueries()
    availability_queries = DjangoAvailabilityQueries()
    return Adapters(
        clock=SystemClock(),
        database=DjangoDatabaseProbe(),
        mailer=SmtpMailer(),
        uow=DjangoUnitOfWork(),
        audit=DjangoAuditLog(),
        users=DjangoUsers(),
        sessions=DjangoSessions(),
        hasher=DjangoPasswordHasher(),
        failures=RedisFailedSignIns(),
        tokens=SecretsTokenGenerator(),
        hospitals=DjangoHospitals(),
        specialties=DjangoSpecialties(),
        departments=DjangoDepartments(),
        rooms=DjangoRooms(),
        appointment_types=DjangoAppointmentTypes(),
        schedule=SchedulingScheduleDependents(usage=availability_queries),
        reference_queries=reference_queries,
        appointments=NoAppointmentsYet(),
        actors=AuditLogActors(DjangoAuditQueries()),
        user_queries=user_queries,
        staff_lookup=user_queries,
        profiles=DjangoClinicianProfiles(),
        staff=IdentityStaffDirectory(lookup=user_queries),
        staff_profiles=OrganisationStaffProfiles(reference_queries),
        scheduling_directory=OrganisationSchedulingDirectory(
            queries=reference_queries, lookup=user_queries
        ),
        availability_rules=DjangoAvailabilityRules(),
        time_offs=DjangoTimeOffs(),
        clinician_appointments=NoClinicianAppointmentsYet(),
        slot_store=DjangoSlotStore(),
        slot_queries=DjangoSlotQueries(),
        availability_queries=availability_queries,
    )


def build_container() -> Container:
    return wire(real_adapters())


_current: Container | None = None


def container() -> Container:
    global _current
    if _current is None:
        _current = build_container()
    return _current


def use_container(replacement: Container | None) -> None:
    """Swap the wiring, e.g. for fakes in tests; None restores the real one."""
    global _current
    _current = replacement
