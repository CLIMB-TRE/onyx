# Generated by Django 5.0.7 on 2024-08-21 15:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data", "0005_remove_choice_project_2_alter_choice_project"),
    ]

    operations = [
        migrations.AlterField(
            model_name="choice",
            name="project",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="data.project"
            ),
        ),
    ]
