from drlibre.bootstrap.container import container
from drlibre.shared_kernel.errors import DomainError, ErrorCode
from drlibre.shared_kernel.ids import Id


def hospital_time_zone(department_id: Id) -> str:
    """Time zone of the hospital holding the department, in which its clinicians' hours read."""
    q = container().reference_queries
    department = q.department(department_id)
    hospital = q.hospital(department.hospital_id) if department else None
    if hospital is None:
        raise DomainError(ErrorCode.NOT_FOUND, "Hôpital introuvable.")
    return hospital.time_zone
