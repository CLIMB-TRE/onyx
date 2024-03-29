# Generated by Django 5.0.3 on 2024-03-12 11:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("accounts", "0001_initial"),
        ("data", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="site",
            name="projects",
            field=models.ManyToManyField(related_name="sites", to="data.project"),
        ),
        migrations.AddField(
            model_name="user",
            name="site",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="accounts.site",
                to_field="code",
            ),
        ),
    ]
