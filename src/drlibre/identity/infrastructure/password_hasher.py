from django.contrib.auth.hashers import UNUSABLE_PASSWORD_PREFIX, check_password, make_password

from drlibre.identity.application.ports.outbound import PasswordHasher


class DjangoPasswordHasher(PasswordHasher):
    def hash(self, raw: str) -> str:
        return make_password(raw)

    def verify(self, raw: str, hashed: str | None) -> bool:
        # An unusable hash makes Django run the default hasher once, so timing matches.
        return check_password(raw, hashed or UNUSABLE_PASSWORD_PREFIX)
