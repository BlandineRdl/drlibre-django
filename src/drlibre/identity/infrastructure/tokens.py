import secrets

from drlibre.identity.application.ports.outbound import TokenGenerator


class SecretsTokenGenerator(TokenGenerator):
    def new_token(self) -> str:
        return secrets.token_urlsafe(32)
