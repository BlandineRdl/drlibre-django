from drlibre.identity.application.ports.outbound import TokenGenerator


class InMemoryTokenGenerator(TokenGenerator):
    def __init__(self) -> None:
        self.issued = 0

    def new_token(self) -> str:
        self.issued += 1
        return f"token-{self.issued}"
