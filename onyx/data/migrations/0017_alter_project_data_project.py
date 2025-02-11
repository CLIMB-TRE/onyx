# Generated by Django 5.0.8 on 2025-02-06 15:06

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data", "0016_project_data_project_is_anal_a9077c_cvr"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="data_project",
            field=models.OneToOneField(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="analysis_project",
                to="data.project",
            ),
        ),
    ]
