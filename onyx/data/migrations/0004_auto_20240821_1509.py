# Generated by Django 5.0.7 on 2024-08-21 15:09

from django.db import migrations


def populate_project_2(apps, schema_editor):
    Choice = apps.get_model("data", "Choice")
    for choice in Choice.objects.all():
        choice.project_2 = choice.project
        choice.save()


class Migration(migrations.Migration):
    dependencies = [
        ("data", "0003_choice_project_2"),
    ]

    operations = [
        migrations.RunPython(populate_project_2),
    ]
