import pytest
from django.db import connection

from drlibre.health.infrastructure.database_probe import DjangoDatabaseProbe

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


def test_probe_reports_postgresql_up() -> None:
    assert connection.vendor == "postgresql"
    assert DjangoDatabaseProbe().is_up() is True
