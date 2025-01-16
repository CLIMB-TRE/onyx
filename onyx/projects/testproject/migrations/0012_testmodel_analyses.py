# Generated by Django 5.0.8 on 2025-01-14 12:13

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data", "0014_analysis_historicalanalysis"),
        ("testproject", "0011_remove_testmodel_analyses"),
    ]

    operations = [
        migrations.AddField(
            model_name="testmodel",
            name="analyses",
            field=models.ManyToManyField(
                help_text="The analyses involving the record.",
                related_name="%(class)s_records",
                to="data.analysis",
            ),
        ),
    ]
