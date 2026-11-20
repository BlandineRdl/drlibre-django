from drlibre.health.application.ports.outbound import DatabaseProbe


class InMemoryDatabaseProbe(DatabaseProbe):
    def __init__(self, *, up: bool = True) -> None:
        self.up = up

    def is_up(self) -> bool:
        return self.up
