from dataclasses import dataclass

from django.conf import settings

from drlibre.audit.application.ports.outbound import AuditLog
from drlibre.audit.infrastructure.audit_log import DjangoAuditLog
from drlibre.audit.infrastructure.queries import DjangoAuditQueries
from drlibre.audit.infrastructure.unit_of_work import DjangoUnitOfWork
from drlibre.booking.application.ports.inbound import (
    BookAppointment,
    CancelAppointment,
    CreateHold,
    ExpireHolds,
    ListPatientAppointments,
    OpenHolds,
    RequirePatient,
    RescheduleAppointment,
    ResendCode,
    SendReminders,
    VerifyHold,
    ViewAppointment,
    ViewHold,
)
from drlibre.booking.application.ports.outbound import (
    Appointments as BookingAppointments,
)
from drlibre.booking.application.ports.outbound import (
    BookingDirectory,
    BookingNotices,
    CodeIssuer,
    FreeSlots,
    Holds,
    PatientAgenda,
    Patients,
    RoundRobinLedger,
    ScheduleLocks,
    VerificationCodes,
    Waitlist,
)
from drlibre.booking.application.ports.outbound import SlotRefresh as BookingSlotRefreshPort
from drlibre.booking.application.use_cases.book_appointment import BookAppointmentUseCase
from drlibre.booking.application.use_cases.cancel_appointment import CancelAppointmentUseCase
from drlibre.booking.application.use_cases.create_hold import CreateHoldUseCase
from drlibre.booking.application.use_cases.expire_holds import ExpireHoldsUseCase
from drlibre.booking.application.use_cases.list_patient_appointments import (
    ListPatientAppointmentsUseCase,
)
from drlibre.booking.application.use_cases.open_holds import OpenHoldsUseCase
from drlibre.booking.application.use_cases.placement import Placement
from drlibre.booking.application.use_cases.require_patient import RequirePatientUseCase
from drlibre.booking.application.use_cases.reschedule_appointment import (
    RescheduleAppointmentUseCase,
)
from drlibre.booking.application.use_cases.resend_code import ResendCodeUseCase
from drlibre.booking.application.use_cases.send_reminders import SendRemindersUseCase
from drlibre.booking.application.use_cases.verify_hold import VerifyHoldUseCase
from drlibre.booking.application.use_cases.view_appointment import ViewAppointmentUseCase
from drlibre.booking.application.use_cases.view_hold import ViewHoldUseCase
from drlibre.booking.infrastructure.booking_slot_refresh import BookingSlotRefresh
from drlibre.booking.infrastructure.code_issuer import HmacCodeIssuer
from drlibre.booking.infrastructure.directory import OrganisationBookingDirectory
from drlibre.booking.infrastructure.free_slots import SchedulingFreeSlots
from drlibre.booking.infrastructure.identity_patients import (
    IdentityPatientAccounts,
    IdentityPatientSessions,
)
from drlibre.booking.infrastructure.outbox_notices import OutboxBookingNotices
from drlibre.booking.infrastructure.patient_agenda import SqlPatientAgenda
from drlibre.booking.infrastructure.patients import IdentityPatients
from drlibre.booking.infrastructure.queries import DjangoBookingQueries
from drlibre.booking.infrastructure.repositories import (
    DjangoAppointments,
    DjangoHolds,
    DjangoVerificationCodes,
    DjangoWaitlist,
)
from drlibre.booking.infrastructure.round_robin_ledger import OrganisationRoundRobinLedger
from drlibre.booking.infrastructure.schedule_locks import DjangoScheduleLocks
from drlibre.health.application.ports.inbound import CheckHealth
from drlibre.health.application.ports.outbound import DatabaseProbe
from drlibre.health.application.use_cases.check_health import CheckHealthUseCase
from drlibre.health.infrastructure.database_probe import DjangoDatabaseProbe
from drlibre.identity.application.ports.inbound import (
    AuthenticateSession,
    ChangePassword,
    DeleteUser,
    OpenPatientSession,
    ProvidePatientAccount,
    RequestSignInLink,
    SaveUser,
    SignIn,
    SignOut,
    StaffLookup,
    UpdateProfile,
    UserQueries,
    UseSignInLink,
)
from drlibre.identity.application.ports.outbound import (
    AuditActors,
    FailedSignIns,
    LinkNotices,
    PasswordHasher,
    Sessions,
    SignInLinks,
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
from drlibre.identity.application.use_cases.open_patient_session import OpenPatientSessionUseCase
from drlibre.identity.application.use_cases.provide_patient_account import (
    ProvidePatientAccountUseCase,
)
from drlibre.identity.application.use_cases.request_sign_in_link import RequestSignInLinkUseCase
from drlibre.identity.application.use_cases.save_user import SaveUserUseCase
from drlibre.identity.application.use_cases.sign_in import SignInUseCase
from drlibre.identity.application.use_cases.sign_out import SignOutUseCase
from drlibre.identity.application.use_cases.update_profile import UpdateProfileUseCase
from drlibre.identity.application.use_cases.use_sign_in_link import UseSignInLinkUseCase
from drlibre.identity.infrastructure.audit_actors import AuditLogActors
from drlibre.identity.infrastructure.failed_sign_ins import RedisFailedSignIns
from drlibre.identity.infrastructure.outbox_link_notices import OutboxLinkNotices
from drlibre.identity.infrastructure.password_hasher import DjangoPasswordHasher
from drlibre.identity.infrastructure.queries import DjangoUserQueries
from drlibre.identity.infrastructure.rate_limiter import RedisRateLimiter
from drlibre.identity.infrastructure.repositories import (
    DjangoSessions,
    DjangoSignInLinks,
    DjangoUsers,
)
from drlibre.identity.infrastructure.staff_profiles import OrganisationStaffProfiles
from drlibre.identity.infrastructure.tokens import SecretsTokenGenerator
from drlibre.identity.infrastructure.upcoming_appointments import BookingUpcomingAppointments
from drlibre.notifications.application.ports.inbound import (
    CountUnread,
    ListNotifications,
    MarkNotificationRead,
    Notify,
)
from drlibre.notifications.application.ports.outbound import Mailer, Notifications
from drlibre.notifications.application.use_cases.count_unread import CountUnreadUseCase
from drlibre.notifications.application.use_cases.list_notifications import (
    ListNotificationsUseCase,
)
from drlibre.notifications.application.use_cases.mark_notification_read import (
    MarkNotificationReadUseCase,
)
from drlibre.notifications.application.use_cases.notify import NotifyUseCase
from drlibre.notifications.application.use_cases.reminded_appointments import (
    RemindedAppointmentsUseCase,
)
from drlibre.notifications.infrastructure.celery_outbox import CeleryEmailOutbox
from drlibre.notifications.infrastructure.repositories import DjangoNotifications
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
from drlibre.organisation.application.use_cases.record_round_robin_assignment import (
    RecordRoundRobinAssignmentUseCase,
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
from drlibre.organisation.infrastructure.schedule_and_booking_dependents import (
    ScheduleAndBookingDependents,
)
from drlibre.organisation.infrastructure.slot_refresh import SchedulingSlotRefresh
from drlibre.organisation.infrastructure.staff_directory import IdentityStaffDirectory
from drlibre.scheduling.application.ports.inbound import (
    AvailabilityQueries,
    DeleteAvailabilityRule,
    DeleteTimeOff,
    ExtendSlotHorizon,
    FindFreeSlots,
    FindFreeWeek,
    NextBookableSlots,
    RecordTimeOff,
    SaveAvailabilityRule,
)
from drlibre.scheduling.application.ports.outbound import (
    AvailabilityRules,
    ClinicianAppointments,
    SchedulingDirectory,
    SlotHolds,
    SlotQueries,
    SlotStore,
    TimeOffs,
)
from drlibre.scheduling.application.use_cases.computed_slots import SlotComputation
from drlibre.scheduling.application.use_cases.delete_availability_rule import (
    DeleteAvailabilityRuleUseCase,
)
from drlibre.scheduling.application.use_cases.delete_time_off import DeleteTimeOffUseCase
from drlibre.scheduling.application.use_cases.extend_slot_horizon import ExtendSlotHorizonUseCase
from drlibre.scheduling.application.use_cases.find_free_slots import FindFreeSlotsUseCase
from drlibre.scheduling.application.use_cases.find_free_week import FindFreeWeekUseCase
from drlibre.scheduling.application.use_cases.free_clinicians_at import FreeCliniciansAtUseCase
from drlibre.scheduling.application.use_cases.is_slot_free import IsSlotFreeUseCase
from drlibre.scheduling.application.use_cases.next_bookable_slots import NextBookableSlotsUseCase
from drlibre.scheduling.application.use_cases.record_time_off import RecordTimeOffUseCase
from drlibre.scheduling.application.use_cases.refresh_slots import RefreshSlotsUseCase
from drlibre.scheduling.application.use_cases.save_availability_rule import (
    SaveAvailabilityRuleUseCase,
)
from drlibre.scheduling.infrastructure.booking_appointments import BookingClinicianAppointments
from drlibre.scheduling.infrastructure.booking_holds import BookingSlotHolds
from drlibre.scheduling.infrastructure.directory import OrganisationSchedulingDirectory
from drlibre.scheduling.infrastructure.queries import DjangoAvailabilityQueries
from drlibre.scheduling.infrastructure.repositories import (
    DjangoAvailabilityRules,
    DjangoTimeOffs,
)
from drlibre.scheduling.infrastructure.slot_queries import DjangoSlotQueries
from drlibre.scheduling.infrastructure.slot_store import DjangoSlotStore
from drlibre.search.application.ports.inbound import (
    CountSearchResults,
    ListFilterOptions,
    SearchHospitals,
    SearchProviders,
    SearchSpecialties,
    ViewHospitalPage,
    ViewProviderPage,
    ViewSpecialtyPage,
)
from drlibre.search.application.ports.outbound import SearchQueries
from drlibre.search.application.use_cases.count_search_results import CountSearchResultsUseCase
from drlibre.search.application.use_cases.list_filter_options import ListFilterOptionsUseCase
from drlibre.search.application.use_cases.search_hospitals import SearchHospitalsUseCase
from drlibre.search.application.use_cases.search_providers import SearchProvidersUseCase
from drlibre.search.application.use_cases.search_specialties import SearchSpecialtiesUseCase
from drlibre.search.application.use_cases.view_hospital_page import ViewHospitalPageUseCase
from drlibre.search.application.use_cases.view_provider_page import ViewProviderPageUseCase
from drlibre.search.application.use_cases.view_specialty_page import ViewSpecialtyPageUseCase
from drlibre.search.infrastructure.sql_queries import SqlSearchQueries
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.rate_limit import RateLimiter
from drlibre.shared_kernel.system_clock import SystemClock
from drlibre.shared_kernel.unit_of_work import UnitOfWork


@dataclass(frozen=True, slots=True)
class BookingAdapters:
    """Outbound adapters of the booking context."""

    appointments: BookingAppointments
    directory: BookingDirectory
    free_slots: FreeSlots
    slot_refresh: BookingSlotRefreshPort
    locks: ScheduleLocks
    patients: Patients
    notices: BookingNotices
    ledger: RoundRobinLedger
    holds: Holds
    open_holds: OpenHolds
    codes: VerificationCodes
    issuer: CodeIssuer
    limiter: RateLimiter
    agenda: PatientAgenda
    waitlist: Waitlist
    network_hourly_limit: int = 20


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
    slot_holds: SlotHolds
    booking: BookingAdapters
    links: SignInLinks
    link_notices: LinkNotices
    search_queries: SearchQueries
    notifications: Notifications
    # Booking's notices write through it, so it is built with them.
    notify: Notify
    # The application's zone, whose date is "today" for a patient's profile.
    time_zone: str
    # None wires organisation to scheduling's own RefreshSlots.
    slot_refresh: SlotRefresh | None = None


@dataclass(frozen=True, slots=True)
class Container:
    clock: Clock
    check_health: CheckHealth
    mailer: Mailer
    sign_in: SignIn
    sign_out: SignOut
    authenticate_session: AuthenticateSession
    change_password: ChangePassword
    update_profile: UpdateProfile
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
    find_free_week: FindFreeWeek
    next_bookable_slots: NextBookableSlots
    book_appointment: BookAppointment
    require_patient: RequirePatient
    create_hold: CreateHold
    verify_hold: VerifyHold
    resend_code: ResendCode
    expire_holds: ExpireHolds
    open_holds: OpenHolds
    view_hold: ViewHold
    view_appointment: ViewAppointment
    list_patient_appointments: ListPatientAppointments
    cancel_appointment: CancelAppointment
    reschedule_appointment: RescheduleAppointment
    send_reminders: SendReminders
    provide_patient_account: ProvidePatientAccount
    open_patient_session: OpenPatientSession
    request_sign_in_link: RequestSignInLink
    use_sign_in_link: UseSignInLink
    search_providers: SearchProviders
    search_hospitals: SearchHospitals
    search_specialties: SearchSpecialties
    count_search_results: CountSearchResults
    list_filter_options: ListFilterOptions
    view_provider_page: ViewProviderPage
    view_hospital_page: ViewHospitalPage
    view_specialty_page: ViewSpecialtyPage
    list_notifications: ListNotifications
    mark_notification_read: MarkNotificationRead
    count_unread: CountUnread


def wire(a: Adapters) -> Container:
    clock, uow, audit = a.clock, a.uow, a.audit
    directory = a.scheduling_directory
    find_free_slots = FindFreeSlotsUseCase(
        clock=clock,
        directory=directory,
        queries=a.slot_queries,
        holds=a.slot_holds,
        computation=SlotComputation(
            directory=directory,
            rules=a.availability_rules,
            time_offs=a.time_offs,
            appointments=a.clinician_appointments,
        ),
    )
    refresh = RefreshSlotsUseCase(
        clock=clock,
        directory=directory,
        rules=a.availability_rules,
        time_offs=a.time_offs,
        appointments=a.clinician_appointments,
        store=a.slot_store,
    )
    slots = a.slot_refresh or SchedulingSlotRefresh(refresh=refresh)
    provide_patient_account = ProvidePatientAccountUseCase(
        clock=clock, uow=uow, audit=audit, users=a.users
    )
    open_patient_session = OpenPatientSessionUseCase(
        clock=clock, uow=uow, audit=audit, users=a.users, sessions=a.sessions, tokens=a.tokens
    )
    booking = _wire_booking(a, provide_patient_account, open_patient_session)
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
        update_profile=UpdateProfileUseCase(
            clock=clock, uow=uow, audit=audit, users=a.users, time_zone=a.time_zone
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
        find_free_slots=find_free_slots,
        find_free_week=FindFreeWeekUseCase(
            clock=clock, directory=directory, find_free_slots=find_free_slots
        ),
        next_bookable_slots=NextBookableSlotsUseCase(clock=clock, find_free_slots=find_free_slots),
        book_appointment=booking.book_appointment,
        require_patient=booking.require_patient,
        create_hold=booking.create_hold,
        verify_hold=booking.verify_hold,
        resend_code=booking.resend_code,
        expire_holds=booking.expire_holds,
        open_holds=booking.open_holds,
        view_hold=booking.view_hold,
        view_appointment=booking.view_appointment,
        list_patient_appointments=booking.list_patient_appointments,
        cancel_appointment=booking.cancel_appointment,
        reschedule_appointment=booking.reschedule_appointment,
        send_reminders=booking.send_reminders,
        provide_patient_account=provide_patient_account,
        open_patient_session=open_patient_session,
        request_sign_in_link=RequestSignInLinkUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            users=a.users,
            links=a.links,
            tokens=a.tokens,
            notices=a.link_notices,
            limiter=a.booking.limiter,
            network_hourly_limit=a.booking.network_hourly_limit,
        ),
        use_sign_in_link=UseSignInLinkUseCase(
            clock=clock,
            uow=uow,
            audit=audit,
            users=a.users,
            sessions=a.sessions,
            links=a.links,
            tokens=a.tokens,
        ),
        search_providers=SearchProvidersUseCase(clock=clock, queries=a.search_queries),
        search_hospitals=SearchHospitalsUseCase(clock=clock, queries=a.search_queries),
        search_specialties=SearchSpecialtiesUseCase(clock=clock, queries=a.search_queries),
        count_search_results=CountSearchResultsUseCase(clock=clock, queries=a.search_queries),
        list_filter_options=ListFilterOptionsUseCase(queries=a.search_queries),
        view_provider_page=ViewProviderPageUseCase(clock=clock, queries=a.search_queries),
        view_hospital_page=ViewHospitalPageUseCase(clock=clock, queries=a.search_queries),
        view_specialty_page=ViewSpecialtyPageUseCase(clock=clock, queries=a.search_queries),
        list_notifications=ListNotificationsUseCase(notifications=a.notifications),
        mark_notification_read=MarkNotificationReadUseCase(
            clock=clock, uow=uow, audit=audit, notifications=a.notifications
        ),
        count_unread=CountUnreadUseCase(notifications=a.notifications),
    )


@dataclass(frozen=True, slots=True)
class _BookingUseCases:
    book_appointment: BookAppointment
    require_patient: RequirePatient
    create_hold: CreateHold
    verify_hold: VerifyHold
    resend_code: ResendCode
    expire_holds: ExpireHolds
    open_holds: OpenHolds
    view_hold: ViewHold
    view_appointment: ViewAppointment
    list_patient_appointments: ListPatientAppointments
    cancel_appointment: CancelAppointment
    reschedule_appointment: RescheduleAppointment
    send_reminders: SendReminders


def _wire_booking(
    a: Adapters, provide: ProvidePatientAccount, open_session: OpenPatientSession
) -> "_BookingUseCases":
    booking = a.booking
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
        holds=booking.holds,
    )
    return _BookingUseCases(
        book_appointment=BookAppointmentUseCase(
            clock=a.clock,
            uow=a.uow,
            placement=placement,
            ledger=booking.ledger,
        ),
        require_patient=RequirePatientUseCase(patients=booking.patients),
        create_hold=CreateHoldUseCase(
            clock=a.clock,
            uow=a.uow,
            audit=a.audit,
            placement=placement,
            holds=booking.holds,
            codes=booking.codes,
            issuer=booking.issuer,
            locks=booking.locks,
            limiter=booking.limiter,
            notices=booking.notices,
            network_hourly_limit=booking.network_hourly_limit,
            time_zone=a.time_zone,
        ),
        verify_hold=VerifyHoldUseCase(
            clock=a.clock,
            uow=a.uow,
            audit=a.audit,
            placement=placement,
            holds=booking.holds,
            codes=booking.codes,
            issuer=booking.issuer,
            accounts=IdentityPatientAccounts(provide),
            sessions=IdentityPatientSessions(open_session),
            ledger=booking.ledger,
        ),
        resend_code=ResendCodeUseCase(
            clock=a.clock,
            uow=a.uow,
            holds=booking.holds,
            codes=booking.codes,
            issuer=booking.issuer,
            limiter=booking.limiter,
            notices=booking.notices,
            network_hourly_limit=booking.network_hourly_limit,
        ),
        expire_holds=ExpireHoldsUseCase(
            clock=a.clock, uow=a.uow, audit=a.audit, holds=booking.holds, codes=booking.codes
        ),
        open_holds=booking.open_holds,
        view_hold=ViewHoldUseCase(clock=a.clock, holds=booking.holds),
        view_appointment=ViewAppointmentUseCase(appointments=booking.appointments),
        list_patient_appointments=ListPatientAppointmentsUseCase(
            clock=a.clock, patients=booking.patients, agenda=booking.agenda
        ),
        cancel_appointment=CancelAppointmentUseCase(
            clock=a.clock,
            uow=a.uow,
            audit=a.audit,
            appointments=booking.appointments,
            locks=booking.locks,
            slot_refresh=booking.slot_refresh,
            notices=booking.notices,
        ),
        reschedule_appointment=RescheduleAppointmentUseCase(
            clock=a.clock,
            uow=a.uow,
            audit=a.audit,
            appointments=booking.appointments,
            directory=booking.directory,
            free_slots=booking.free_slots,
            placement=placement,
            locks=booking.locks,
            slot_refresh=booking.slot_refresh,
            notices=booking.notices,
        ),
        send_reminders=SendRemindersUseCase(
            clock=a.clock,
            uow=a.uow,
            audit=a.audit,
            appointments=booking.appointments,
            notices=booking.notices,
        ),
    )


def real_adapters(clock: Clock | None = None) -> Adapters:
    clock = clock or SystemClock()
    user_queries = DjangoUserQueries()
    reference_queries = DjangoReferenceQueries()
    availability_queries = DjangoAvailabilityQueries()
    scheduling_directory = OrganisationSchedulingDirectory(
        queries=reference_queries, lookup=user_queries
    )
    profiles = DjangoClinicianProfiles()
    # Booking's queries and holds depend on nothing, so scheduling can read them first.
    booking_queries = DjangoBookingQueries()
    booking_holds = DjangoHolds()
    open_holds = OpenHoldsUseCase(holds=booking_holds)
    slot_holds = BookingSlotHolds(open_holds)
    clinician_appointments = BookingClinicianAppointments(booking_queries)
    rules, time_offs = DjangoAvailabilityRules(), DjangoTimeOffs()
    slot_store, slot_queries = DjangoSlotStore(), DjangoSlotQueries()
    # Scheduling's inbound ports booking reaches, built once from the adapters above.
    refresh = RefreshSlotsUseCase(
        clock=clock,
        directory=scheduling_directory,
        rules=rules,
        time_offs=time_offs,
        appointments=clinician_appointments,
        store=slot_store,
    )
    is_slot_free = IsSlotFreeUseCase(
        clock=clock,
        directory=scheduling_directory,
        queries=slot_queries,
        holds=slot_holds,
        computation=SlotComputation(
            directory=scheduling_directory,
            rules=rules,
            time_offs=time_offs,
            appointments=clinician_appointments,
        ),
    )
    free_clinicians_at = FreeCliniciansAtUseCase(
        clock=clock, directory=scheduling_directory, queries=slot_queries, holds=slot_holds
    )
    patients = IdentityPatients(user_queries)
    # Notifications depend on nothing; booking's notices write through them.
    notifications = DjangoNotifications()
    notify = NotifyUseCase(clock=clock, notifications=notifications)
    booking_directory = OrganisationBookingDirectory(queries=reference_queries, staff=user_queries)
    return Adapters(
        clock=clock,
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
        schedule=ScheduleAndBookingDependents(
            usage=availability_queries, appointments=booking_queries
        ),
        reference_queries=reference_queries,
        appointments=BookingUpcomingAppointments(booking_queries),
        actors=AuditLogActors(DjangoAuditQueries()),
        user_queries=user_queries,
        staff_lookup=user_queries,
        profiles=profiles,
        staff=IdentityStaffDirectory(lookup=user_queries),
        staff_profiles=OrganisationStaffProfiles(reference_queries),
        scheduling_directory=scheduling_directory,
        availability_rules=rules,
        time_offs=time_offs,
        clinician_appointments=clinician_appointments,
        slot_store=slot_store,
        slot_queries=slot_queries,
        slot_holds=slot_holds,
        availability_queries=availability_queries,
        slot_refresh=SchedulingSlotRefresh(refresh=refresh),
        booking=BookingAdapters(
            appointments=DjangoAppointments(),
            directory=booking_directory,
            free_slots=SchedulingFreeSlots(is_slot_free, free_clinicians_at),
            slot_refresh=BookingSlotRefresh(refresh),
            locks=DjangoScheduleLocks(),
            patients=patients,
            notices=OutboxBookingNotices(
                outbox=CeleryEmailOutbox(),
                notify=notify,
                reminded=RemindedAppointmentsUseCase(notifications=notifications),
                directory=booking_directory,
                patients=patients,
                public_base_url=settings.PUBLIC_BASE_URL,
            ),
            ledger=OrganisationRoundRobinLedger(
                RecordRoundRobinAssignmentUseCase(profiles=profiles)
            ),
            holds=booking_holds,
            open_holds=open_holds,
            codes=DjangoVerificationCodes(),
            issuer=HmacCodeIssuer(key=settings.SECRET_KEY),
            limiter=RedisRateLimiter(prefix=settings.RATE_LIMIT_PREFIX),
            agenda=SqlPatientAgenda(),
            waitlist=DjangoWaitlist(),
            network_hourly_limit=settings.NETWORK_HOURLY_LIMIT,
        ),
        links=DjangoSignInLinks(),
        link_notices=OutboxLinkNotices(
            outbox=CeleryEmailOutbox(), public_base_url=settings.PUBLIC_BASE_URL
        ),
        search_queries=SqlSearchQueries(),
        notifications=notifications,
        notify=notify,
        time_zone=settings.TIME_ZONE,
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
