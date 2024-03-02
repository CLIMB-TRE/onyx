import hashlib
from datetime import date
from rest_framework import serializers, exceptions
from django.utils.translation import gettext_lazy as _
from data.models import Choice, Anonymiser, Anonymiser2
from accounts.models import Site
from utils.functions import get_suggestions


# TODO: Do we even need this?
class YearMonthField(serializers.Field):
    def to_internal_value(self, data):
        try:
            year, month = str(data).split("-")
            if not (len(year) == 4 and 1 <= len(month) <= 2):
                raise ValueError
            value = date(int(year), int(month), 1)
        except ValueError:
            raise exceptions.ValidationError("Enter a valid date in YYYY-MM format.")

        return value

    def to_representation(self, value):
        try:
            year, month, _ = str(value).split("-")
        except ValueError:
            raise exceptions.ValidationError("Must be in YYYY-MM-DD format.")

        return year + "-" + month


class ChoiceField(serializers.ChoiceField):
    default_error_messages = {"invalid_choice": _("{suggestions}")}

    def __init__(self, project, field, **kwargs):
        self.project = project
        self.field = field
        super().__init__([], **kwargs)

    def to_internal_value(self, data):
        data = str(data).strip().lower()

        self.choices = list(
            Choice.objects.filter(
                project_id=self.project,
                field=self.field,
                is_active=True,
            ).values_list(
                "choice",
                flat=True,
            )
        )
        self.choice_map = {choice.lower().strip(): choice for choice in self.choices}

        if data in self.choice_map:
            data = self.choice_map[data]

        if data == "" and self.allow_blank:
            return ""

        try:
            return self.choice_strings_to_values[data]
        except KeyError:
            self.fail(
                "invalid_choice",
                suggestions=get_suggestions(
                    data,
                    options=self.choices,
                    n=1,
                    message_prefix="Select a valid choice.",
                ),
            )


class SiteField(ChoiceField):
    default_error_messages = {
        "does_not_exist": _("Site with code={value} does not exist."),
        "invalid": _("Invalid value."),
    }

    def __init__(self, project, **kwargs):
        super().__init__(project, "site", **kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data)
        try:
            return Site.objects.get(code=value)
        except Site.DoesNotExist:
            self.fail("does_not_exist", value=value)
        except (TypeError, ValueError):
            self.fail("invalid")

    def to_representation(self, site):
        return site.code


class AnonymiserField(serializers.CharField):
    def __init__(self, anonymiser_model: type[Anonymiser], **kwargs):
        self.anonymiser_model = anonymiser_model
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip().lower()

        hasher = hashlib.sha256()
        hasher.update(value.encode("utf-8"))
        value = hasher.hexdigest()

        anonymiser, _ = self.anonymiser_model.objects.get_or_create(hash=value)
        value = anonymiser.identifier

        return value


class AnonymiserField2(serializers.CharField):
    def __init__(self, project, prefix, **kwargs):
        self.project = project
        self.prefix = prefix
        super().__init__(**kwargs)

    def to_internal_value(self, data):
        value = super().to_internal_value(data).strip().lower()

        hasher = hashlib.sha256()
        hasher.update(value.encode("utf-8"))
        value = hasher.hexdigest()

        # Should the identifier generation/retrieval happen in the object-level validate method ?
        # Would that allow for max length / min length validators to work correctly ?
        anonymiser, _ = Anonymiser2.objects.get_or_create(
            project=self.project,
            site=self.context["site"],
            prefix=self.prefix,
            hash=value,
        )
        value = anonymiser.identifier

        return value
