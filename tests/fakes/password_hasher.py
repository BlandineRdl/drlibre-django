from drlibre.identity.application.ports.outbound import PasswordHasher


class InMemoryPasswordHasher(PasswordHasher):
    """Reversible stand-in hash; counts verifications to prove equal work on every path."""

    def __init__(self) -> None:
        self.verifications = 0

    def hash(self, raw: str) -> str:
        return f"hashed:{raw}"

    def verify(self, raw: str, hashed: str | None) -> bool:
        self.verifications += 1
        return hashed is not None and hashed == self.hash(raw)
