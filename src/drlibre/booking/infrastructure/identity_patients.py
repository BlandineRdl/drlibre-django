from datetime import date

from drlibre.booking.application.ports.outbound import (
    OpenedSession,
    PatientAccounts,
    PatientSessions,
)
from drlibre.identity.application.ports.inbound import OpenPatientSession, ProvidePatientAccount
from drlibre.shared_kernel.ids import Id


class IdentityPatientAccounts(PatientAccounts):
    def __init__(self, provide: ProvidePatientAccount) -> None:
        self._provide = provide

    def provide(self, *, full_name: str, email: str, birth_date: date, phone: str | None) -> Id:
        return self._provide.execute(
            full_name=full_name, email=email, birth_date=birth_date, phone=phone
        )


class IdentityPatientSessions(PatientSessions):
    def __init__(self, open_session: OpenPatientSession) -> None:
        self._open = open_session

    def open(self, *, patient_id: Id, user_agent: str) -> OpenedSession:
        signed_in = self._open.execute(patient_id=patient_id, user_agent=user_agent)
        return OpenedSession(signed_in.token, signed_in.expires_at)
