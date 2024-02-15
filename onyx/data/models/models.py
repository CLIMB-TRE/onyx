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
from utils.fields import StrippedCharField, LowerCharField, UpperCharField
from utils.constraints import unique_together
from simple_history.models import HistoricalRecords
from ..types import ALL_LOOKUPS


class Project(models.Model):
    code = LowerCharField(max_length=50, unique=True)
    name = StrippedCharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)


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


# TODO: Change project to namespace? Or omit it entirely?
# TODO: Possibly some additional model, ChoiceLink, to link different names to the same set of choices?
# At the moment, to work with the filters, the field name must match the choice
class Choice(models.Model):
    project = models.ForeignKey(Project, to_field="code", on_delete=models.CASCADE)
    field = models.TextField()
    choice = models.TextField()
    is_active = models.BooleanField(default=True)
    constraints = models.ManyToManyField("Choice", related_name="reverse_constraints")

    class Meta:
        indexes = [
            models.Index(fields=["project", "field"]),
        ]
        constraints = [
            unique_together(
                fields=["project", "field", "choice"],
            ),
        ]


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


class BaseRecord(models.Model):
    # TODO: Make uuid primary key?
    # Stop worrying about collisions. its not going to happen m8
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    history = HistoricalRecords(inherit=True)
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # TODO: Display sites again
    # site = models.ForeignKey(Site, to_field="code", on_delete=models.CASCADE)

    class Meta:
        abstract = True

    @classmethod
    def check(cls, **kwargs: Any) -> list[CheckMessage]:
        errors = super().check(**kwargs)

        for field in cls._meta.get_fields():
            if field.name in ALL_LOOKUPS:
                errors.append(
                    checks.Error(
                        f"Field names must not match existing lookups.",
                        obj=field,
                    )
                )

        return errors


class ProjectRecord(BaseRecord):
    @classmethod
    def version(cls):
        raise NotImplementedError("A version number is required.")

    climb_id = UpperCharField(
        max_length=12,
        unique=True,
        help_text="Unique identifier for a project record in Onyx.",
    )
    is_published = models.BooleanField(
        default=True,
        help_text="Indicator for whether a project record has been published.",
    )
    published_date = models.DateField(
        null=True,
        help_text="The date the project record was published in Onyx.",
    )
    is_suppressed = models.BooleanField(
        default=False,
        help_text="Indicator for whether a project record has been hidden from users.",
    )
    is_site_restricted = models.BooleanField(
        default=False,
        help_text="Indicator for whether a project record has been hidden from users not within the record's site.",
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.pk:
            climb_id = ClimbID.objects.create()
            self.climb_id = climb_id.climb_id

        if self.published_date is None and self.is_published:
            self.published_date = datetime.today().date()

        super().save(*args, **kwargs)


class Anonymiser(models.Model):
    hash = models.TextField(unique=True)
    identifier = UpperCharField(unique=True, max_length=12)

    class Meta:
        abstract = True

    @classmethod
    def get_identifier_prefix(cls) -> str:
        """
        Get the prefix for the identifier.
        """
        raise NotImplementedError("A prefix is required.")

    @classmethod
    def generate_identifier(cls) -> str:
        """
        Generate a random new identifier on the given `model`.

        The identifier consists of the given `prefix`, followed by a `-`, followed by 10 random hexadecimal numbers.

        This means there are `16^10 = 1,099,511,627,776` identifiers to choose from for a given `model` and `prefix`.
        """

        identifier = cls.get_identifier_prefix() + "-" + "".join(token_hex(5).upper())

        if cls.objects.filter(identifier=identifier).exists():
            identifier = cls.generate_identifier()

        return identifier

    def save(self, *args, **kwargs):
        if not self.identifier:
            self.identifier = self.generate_identifier()

        super().save(*args, **kwargs)
