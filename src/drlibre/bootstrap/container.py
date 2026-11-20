from dataclasses import dataclass

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.audit.infrastructure.queries import DjangoAuditQueries
from drlibre.audit.infrastructure.unit_of_work import DjangoUnitOfWork
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
from drlibre.organisation.infrastructure.schedule_dependents import NoScheduleYet
from drlibre.organisation.infrastructure.staff_directory import IdentityStaffDirectory
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.system_clock import SystemClock
from drlibre.shared_kernel.unit_of_work import UnitOfWork


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


@dataclass(frozen=True, slots=True)
class Container:
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


def wire(a: Adapters) -> Container:
    clock, uow, audit = a.clock, a.uow, a.audit
    return Container(
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
        save_hospital=SaveHospitalUseCase(clock=clock, uow=uow, audit=audit, hospitals=a.hospitals),
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
            clock=clock, uow=uow, audit=audit, departments=a.departments, hospitals=a.hospitals
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
            profiles=a.profiles,
            departments=a.departments,
            specialties=a.specialties,
            rooms=a.rooms,
        ),
        delete_clinician_profile=DeleteClinicianProfileUseCase(
            clock=clock, uow=uow, audit=audit, profiles=a.profiles, schedule=a.schedule
        ),
    )


def real_adapters() -> Adapters:
    user_queries = DjangoUserQueries()
    reference_queries = DjangoReferenceQueries()
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
        schedule=NoScheduleYet(),
        reference_queries=reference_queries,
        appointments=NoAppointmentsYet(),
        actors=AuditLogActors(DjangoAuditQueries()),
        user_queries=user_queries,
        staff_lookup=user_queries,
        profiles=DjangoClinicianProfiles(),
        staff=IdentityStaffDirectory(lookup=user_queries),
        staff_profiles=OrganisationStaffProfiles(reference_queries),
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
