# Generated by Django 5.0.8 on 2025-02-06 14:07

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("data", "0015_project_data_project_project_is_analysis_project"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="project",
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(("is_analysis_project", True), _negated=True),
                    ("data_project__isnull", False),
                    _connector="OR",
                ),
                name="data_project_is_anal_a9077c_cvr",
                violation_error_message="Each of data_project are required in order to set is_analysis_project to the value.",
            ),
        ),
    ]
