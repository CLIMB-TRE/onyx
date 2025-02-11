from django.db import models
from django.contrib.postgres.fields import ArrayField
from utils.fields import UpperCharField, ChoiceField
from utils.constraints import (
    unique_together,
    optional_value_group,
    ordering,
    non_futures,
    conditional_required,
    conditional_value_required,
)
from data.models import BaseRecord, ProjectRecord


# TODO: Switch all usage of FloatField to DecimalField?


__version__ = "0.1.0"


class BaseTestProject(ProjectRecord):
    @classmethod
    def version(cls):
        return __version__

    sample_id = UpperCharField(max_length=50)
    run_name = UpperCharField(max_length=100)
    collection_month = models.DateField(null=True)
    received_month = models.DateField(null=True)
    char_max_length_20 = models.CharField(max_length=20)
    text_option_1 = models.TextField(blank=True)
    text_option_2 = models.TextField(blank=True)
    submission_date = models.DateField(null=True)
    country = ChoiceField(max_length=20, blank=True)
    region = ChoiceField(max_length=20, blank=True)
    concern = models.BooleanField(null=True)
    tests = models.IntegerField(null=True)
    score = models.FloatField(null=True)
    start = models.IntegerField()
    end = models.IntegerField()
    required_when_published = models.TextField(blank=True)
    scores = ArrayField(models.IntegerField(), default=list, size=10)
    structure = models.JSONField(default=dict)

    class Meta:
        abstract = True
        default_permissions = []
        indexes = [
            models.Index(fields=["created"]),
            models.Index(fields=["climb_id"]),
            models.Index(fields=["is_published"]),
            models.Index(fields=["published_date"]),
            models.Index(fields=["is_suppressed"]),
            models.Index(fields=["site"]),
            models.Index(fields=["is_site_restricted"]),
            models.Index(fields=["sample_id", "run_name"]),
            models.Index(fields=["sample_id"]),
            models.Index(fields=["run_name"]),
            models.Index(fields=["collection_month"]),
            models.Index(fields=["received_month"]),
        ]
        constraints = [
            unique_together(
                fields=["sample_id", "run_name"],
            ),
            optional_value_group(
                fields=["collection_month", "received_month"],
            ),
            optional_value_group(
                fields=["text_option_1", "text_option_2"],
            ),
            ordering(
                fields=("collection_month", "received_month"),
            ),
            ordering(
                fields=("start", "end"),
            ),
            non_futures(
                fields=["collection_month", "received_month", "submission_date"],
            ),
            conditional_required(
                field="region",
                required=["country"],
            ),
            conditional_value_required(
                field="is_published",
                value=True,
                required=["published_date"],
            ),
            conditional_value_required(
                field="is_published",
                value=True,
                required=["required_when_published"],
            ),
        ]


class BaseTestProjectRecord(BaseRecord):
    test_id = models.IntegerField()
    test_pass = models.BooleanField()
    test_start = models.DateField()
    test_end = models.DateField()
    score_a = models.FloatField(null=True)
    score_b = models.FloatField(null=True)
    score_c = models.FloatField(null=True)
    test_result = models.TextField(blank=True)

    class Meta:
        abstract = True
        default_permissions = []
        indexes = [
            models.Index(fields=["created"]),
            models.Index(fields=["link", "test_id"]),
            models.Index(fields=["test_id"]),
            models.Index(fields=["test_pass"]),
            models.Index(fields=["test_start"]),
            models.Index(fields=["test_end"]),
            models.Index(fields=["score_a"]),
            models.Index(fields=["score_b"]),
            models.Index(fields=["score_c"]),
            models.Index(fields=["test_result"]),
        ]
        constraints = [
            unique_together(
                fields=["link", "test_id"],
            ),
            optional_value_group(
                fields=["score_a", "score_b"],
            ),
            ordering(
                fields=("test_start", "test_end"),
            ),
            conditional_required(
                field="score_c",
                required=["score_a", "score_b"],
            ),
            conditional_value_required(
                field="test_pass",
                value=True,
                required=["test_result"],
            ),
        ]


class TestProject(BaseTestProject):
    pass


class TestProjectRecord(BaseTestProjectRecord):
    link = models.ForeignKey(
        TestProject, on_delete=models.CASCADE, related_name="records"
    )
