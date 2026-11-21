from argparse import ArgumentParser
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from drlibre.bootstrap.container import container
from drlibre.shared_kernel.errors import DomainError


class Command(BaseCommand):
    help = "Issue a bearer token for a user, shown once, or revoke all their tokens."

    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument("email")
        parser.add_argument("--days", type=int, default=90)
        parser.add_argument("--label", default="cli")
        parser.add_argument("--revoke", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        app = container()
        try:
            if options["revoke"]:
                count = app.revoke_api_tokens.execute(user_email=options["email"])
                self.stdout.write(f"{count} jeton(s) révoqué(s).")
                return
            token = app.issue_api_token.execute(
                user_email=options["email"], label=options["label"], days=options["days"]
            )
        except DomainError as error:
            raise CommandError(error.message) from error
        self.stdout.write(token)
