# Generated by Django 5.0.7 on 2024-08-21 15:08

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data", "0002_choice_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="choice",
            name="project_2",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="choices",
                to="data.project",
            ),
        ),
    ]