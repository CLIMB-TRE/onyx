from typing import Any
import uuid
from datetime import datetime
from secrets import token_hex
from django.db import models
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core import checks
from django.core.checks.messages import CheckMessage
from accounts.models import Site, User
from utils.fields import StrippedCharField, LowerCharField, UpperCharField, SiteField
from utils.constraints import (
    unique_together,
    non_futures,
    conditional_value_required,
    conditional_value_optional_value_group,
)
from simple_history.models import HistoricalRecords
from .types import OnyxLookup


class Project(models.Model):
    code = LowerCharField(max_length=50, unique=True)
    name = StrippedCharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT)

    def __str__(self):
        return self.code


class ProjectGroup(models.Model):
    group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        primary_key=True,
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    scope = LowerCharField(max_length=50)
    actions = models.TextField(blank=True)

    class Meta:
        constraints = [
            unique_together(
                fields=["project", "scope"],
            ),
        ]

    def __str__(self):
        return self.group.name


# TODO: Change project to namespace? Or omit it entirely?
# TODO: Possibly some additional model, ChoiceLink, to link different names to the same set of choices?
# At the moment, to work with the filters, the field name must match the choice
class Choice(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    field = models.TextField()
    choice = models.TextField()
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    constraints = models.ManyToManyField("self")

    class Meta:
        indexes = [
            models.Index(fields=["project", "field"]),
        ]
        constraints = [
            unique_together(
                fields=["project", "field", "choice"],
            ),
        ]

    def __str__(self):
        return f"{self.project.code} | {self.field} | {self.choice}"


class Anonymiser(models.Model):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    site = models.ForeignKey(Site, on_delete=models.PROTECT)
    field = LowerCharField(max_length=100)
    prefix = UpperCharField(max_length=5)
    hash = models.TextField()
    identifier = UpperCharField(unique=True, max_length=20)

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "project",
                    "site",
                    "field",
                    "hash",
                ]
            ),
        ]
        constraints = [
            unique_together(
                fields=[
                    "project",
                    "site",
                    "field",
                    "hash",
                ],
            ),
        ]

    def generate_identifier(self) -> str:
        """
        Generate a random unique identifier.

        The identifier consists of the instance's `prefix`, followed by 10 random hexadecimal numbers.

        This means there are `16^10 = 1,099,511,627,776` identifiers to choose from.
        """

        identifier = self.prefix + token_hex(5).upper()

        if Anonymiser.objects.filter(identifier=identifier).exists():
            identifier = self.generate_identifier()

        return identifier

    def save(self, *args, **kwargs):
        if not self.identifier:
            self.identifier = self.generate_identifier()

        super().save(*args, **kwargs)

    def __str__(self):
        return self.identifier


class BaseRecord(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    history = HistoricalRecords(inherit=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        abstract = True

    @classmethod
    def check(cls, **kwargs: Any) -> list[CheckMessage]:
        errors = super().check(**kwargs)

        for field in cls._meta.get_fields():
            if field.name in OnyxLookup.lookups():
                errors.append(
                    checks.Error(
                        "Field names must not match existing lookups.",
                        obj=field,
                    )
                )

            elif field.name == "count":
                errors.append(
                    checks.Error(
                        "Field name cannot be 'count' as this is reserved.",
                        obj=field,
                    )
                )

        return errors

    def __str__(self):
        return str(self.uuid)


class PrimaryRecord(BaseRecord):
    @classmethod
    def version(cls):
        return "N/A"

    is_published = models.BooleanField(
        default=True,
        help_text="Indicator for whether an object has been published.",
    )
    published_date = models.DateField(
        null=True,
        help_text="The date the object was published in Onyx.",
    )
    is_suppressed = models.BooleanField(
        default=False,
        help_text="Indicator for whether an object has been hidden from users.",
    )
    site = SiteField(
        Site,
        to_field="code",
        on_delete=models.PROTECT,
        help_text="Site that uploaded the object.",
    )
    is_site_restricted = models.BooleanField(
        default=False,
        help_text="Indicator for whether an object has been hidden from users not within the object's site.",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.published_date is None and self.is_published:
            self.published_date = datetime.today().date()

        super().save(*args, **kwargs)


def generate_analysis_id():
    """
    Generate a random new Analysis ID.

    The Analysis ID consists of the prefix `A-` followed by 10 random hexadecimal numbers.

    This means there are `16^10 = 1,099,511,627,776` Analysis IDs to choose from.
    """
    analysis_id = "A-" + "".join(token_hex(5).upper())

    if Analysis.objects.filter(analysis_id=analysis_id).exists():
        analysis_id = generate_analysis_id()

    return analysis_id


class Analysis(PrimaryRecord):
    project = models.ForeignKey(Project, on_delete=models.PROTECT)

    # Overview
    # Auto-generated
    analysis_id = UpperCharField(
        default=generate_analysis_id,
        max_length=12,
        unique=True,
        help_text="Unique identifier for an analysis in Onyx.",
    )
    # Required
    analysis_date = models.DateField(
        help_text="The date the analysis was carried out.",
    )
    # Required
    name = StrippedCharField(
        max_length=50,
        help_text="Name for the analysis, unique to the project.",
    )
    # Optional
    description = models.CharField(
        blank=True,
        max_length=500,
        help_text="Description of the analysis.",
    )

    # Execution
    # Required
    pipeline_name = models.CharField(
        max_length=50,
        help_text="Name of the pipeline used for the analysis.",
    )
    # Required
    pipeline_version = models.CharField(
        max_length=10,
        help_text="Version of the pipeline used for the analysis.",
    )
    # Optional
    pipeline_url = models.CharField(
        blank=True,
        max_length=200,
        help_text="URL to the pipeline used for the analysis.",
    )
    # Optional
    pipeline_command = models.CharField(
        blank=True,
        max_length=200,
        help_text="Command used to run the pipeline for the analysis.",
    )
    # Optional (has default)
    methods = models.JSONField(
        default=dict,
        help_text="Structured details of the experiment run and its inputs.",
    )

    # Results
    # Required if published
    result = models.CharField(
        blank=True,
        max_length=200,
        help_text="Key findings of the analysis.",
    )
    # Optional (has default)
    result_metrics = models.JSONField(
        default=dict,
        help_text="Structured output metrics from the result of the analysis.",
    )
    # One of report or outputs required if published
    report = models.CharField(
        blank=True,
        max_length=200,
        help_text="HTML report produced from the analysis.",
    )
    outputs = models.CharField(
        blank=True,
        max_length=200,
        help_text="Directory of outputs produced from the analysis.",
    )

    # Relationships
    # Optional
    upstream_analyses = models.ManyToManyField(
        "self",
        symmetrical=False,
        null=True,
        related_name="downstream_analyses",
        help_text="The analyses that this analysis depends on.",
    )
    # Optional
    identifiers = models.ManyToManyField(
        Anonymiser,
        related_name="analyses",
        help_text="Key anonymised identifiers involved in the analysis. This does not include the CLIMB ID (for these, see the {project}_records field).",
    )

    class Meta:
        indexes = [
            models.Index(
                fields=[
                    "project",
                    "analysis_id",
                    "analysis_date",
                    "name",
                    "result",
                ]
            ),
        ]
        constraints = [
            non_futures(
                fields=["analysis_date"],
            ),
            conditional_value_required(
                field="is_published",
                value=True,
                required=["result"],
            ),
            conditional_value_optional_value_group(
                field="is_published",
                value=True,
                optional=["report", "outputs"],
            ),
        ]

    def __str__(self):
        return self.analysis_id


def generate_climb_id():
    """
    Generate a random new CLIMB ID.

    The CLIMB ID consists of the prefix `C-` followed by 10 random hexadecimal numbers.

    This means there are `16^10 = 1,099,511,627,776` CLIMB IDs to choose from.
    """
    climb_id = "C-" + "".join(token_hex(5).upper())

    if ClimbID.objects.filter(climb_id=climb_id).exists():
        climb_id = generate_climb_id()

    return climb_id


class ClimbID(models.Model):
    climb_id = UpperCharField(default=generate_climb_id, max_length=12, unique=True)

    def __str__(self):
        return self.climb_id


class ProjectRecord(PrimaryRecord):
    @classmethod
    def version(cls):
        raise NotImplementedError("A version number is required.")

    climb_id = UpperCharField(
        max_length=12,
        unique=True,
        help_text="Unique identifier for a project record in Onyx.",
    )
    analyses = models.ManyToManyField(
        Analysis,
        related_name="%(class)s_records",
        help_text="The analyses involving the record.",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.pk:
            climb_id = ClimbID.objects.create()
            self.climb_id = climb_id.climb_id

        super().save(*args, **kwargs)

    def __str__(self):
        return self.climb_id
