from collections.abc import Mapping

from drlibre.audit.application.ports.outbound import AuditEntry, AuditLog
from drlibre.organisation.application.ports.inbound import AttachClinicianProfile
from drlibre.organisation.application.ports.outbound import (
    ClinicianProfiles,
    Departments,
    Rooms,
    Specialties,
    StaffDirectory,
)
from drlibre.organisation.application.use_cases.clinician_profile_rules import check_references
from drlibre.organisation.domain.clinician_profile import ClinicianProfile
from drlibre.shared_kernel.clock import Clock
from drlibre.shared_kernel.ids import Id
from drlibre.shared_kernel.unit_of_work import UnitOfWork
from drlibre.shared_kernel.validation import invalid_field, parse_id


class AttachClinicianProfileUseCase(AttachClinicianProfile):
    def __init__(
        self,
        *,
        clock: Clock,
        uow: UnitOfWork,
        audit: AuditLog,
        profiles: ClinicianProfiles,
        staff: StaffDirectory,
        departments: Departments,
        specialties: Specialties,
        rooms: Rooms,
    ) -> None:
        self._clock = clock
        self._uow = uow
        self._audit = audit
        self._profiles = profiles
        self._staff = staff
        self._departments = departments
        self._specialties = specialties
        self._rooms = rooms

    def execute(self, *, actor: Id | None, user_id: str, fields: Mapping[str, str]) -> Id:
        clinician_id = parse_id(user_id)
        if clinician_id is None or self._staff.active_clinician(clinician_id) is None:
            raise invalid_field("user_id", "Choisissez un praticien actif.")
        if self._profiles.for_user(clinician_id) is not None:
            raise invalid_field("user_id", "Ce praticien a déjà un profil.")
        at = self._clock.now()
        profile = ClinicianProfile.attach(fields, user_id=clinician_id, at=at)
        check_references(
            profile, departments=self._departments, specialties=self._specialties, rooms=self._rooms
        )
        with self._uow:
            self._profiles.save(profile)
            self._audit.record(
                AuditEntry.from_event(
                    actor=actor,
                    action="clinician_profile.created",
                    entity_type="clinician_profile",
                    entity_id=profile.id,
                    at=at,
                    metadata={"user": clinician_id, "department": profile.department_id},
                )
            )
        return profile.id
