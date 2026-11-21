from datetime import datetime

from drlibre.identity.application.ports.outbound import SignInLinks
from drlibre.identity.domain.sign_in_link import SignInLink
from drlibre.shared_kernel.ids import Id


class InMemorySignInLinks(SignInLinks):
    def __init__(self) -> None:
        self.rows: dict[Id, SignInLink] = {}

    def add(self, link: SignInLink) -> None:
        self.rows[link.id] = link

    def by_token_hash(self, token_hash: str) -> SignInLink | None:
        return next((r for r in self.rows.values() if r.token_hash == token_hash), None)

    def cancel_open_for(self, patient_id: Id, *, at: datetime) -> None:
        for link in list(self.rows.values()):
            if link.patient_id == patient_id and link.used_at is None and link.cancelled_at is None:
                self.rows[link.id] = link.cancelled(at)

    def save(self, link: SignInLink) -> None:
        self.rows[link.id] = link
