# Generated by Django 5.0.8 on 2024-09-10 12:53

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("testproject", "0008_historicaltestmodel_scores_testmodel_scores"),
    ]

    operations = [
        migrations.AddField(
            model_name="historicaltestmodel",
            name="structure",
            field=models.JSONField(default=dict),
        ),
        migrations.AddField(
            model_name="testmodel",
            name="structure",
            field=models.JSONField(default=dict),
        ),
    ]
