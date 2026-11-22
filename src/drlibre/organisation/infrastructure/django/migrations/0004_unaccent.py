from django.contrib.postgres.operations import UnaccentExtension
from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("organisation", "0003_record_provenance")]

    operations = [UnaccentExtension()]
