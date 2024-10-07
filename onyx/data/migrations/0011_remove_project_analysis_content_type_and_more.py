# Generated by Django 5.0.8 on 2024-09-12 18:29

import data.models
import utils.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data", "0010_analysis_delete_analysisid"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="project",
            name="analysis_content_type",
        ),
        migrations.AlterField(
            model_name="analysis",
            name="analysis_id",
            field=utils.fields.UpperCharField(
                default=data.models.generate_analysis_id,
                help_text="Unique identifier for an analysis in Onyx.",
                max_length=12,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="analysis",
            name="published_date",
            field=models.DateField(
                auto_now_add=True,
                help_text="The date the analysis was published in Onyx.",
            ),
        ),
    ]