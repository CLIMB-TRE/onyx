from django.db import migrations
from data.migration_utils import backfill_published_timestamp


def backfill(apps, schema_editor):
    backfill_published_timestamp(
        apps.get_model("data", "Analysis"),
        apps.get_model("data", "HistoricalAnalysis"),
    )


class Migration(migrations.Migration):

    dependencies = [
        ("data", "0016_published_timestamp"),
    ]

    operations = [
        migrations.RunPython(backfill, migrations.RunPython.noop),
    ]
