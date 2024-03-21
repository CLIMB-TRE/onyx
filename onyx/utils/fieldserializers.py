from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from data.models import Choice
from accounts.models import Site
from utils.functions import get_suggestions


class CharField(serializers.CharField):
    def to_internal_value(self, data):
        data = super().to_internal_value(data)

        if data.upper().strip() in {
            "NA",
            "N/A",
            "N.A.",
            "N.A",
            "EMPTY",
            "NULL",
            "NONE",
            "NADA",
        }:
            raise serializers.ValidationError(
                "Cannot provide text representing empty data."
            )

        return data


class DateField(serializers.DateField):
    def __init__(self, format: str, input_formats=None, **kwargs):
        super().__init__(
            format,  #  type: ignore
            input_formats=input_formats,
            **kwargs,
        )

    def to_internal_value(self, data):
        if self.allow_null and not str(data).strip():
            return None

        return super().to_internal_value(data)


class ChoiceField(serializers.ChoiceField):
    default_error_messages = {"invalid_choice": _("{suggestions}")}

    def __init__(self, field, **kwargs):
        self.field = field
        super().__init__([], **kwargs)

    def to_internal_value(self, data):
        data = str(data).strip().lower()

        self.choices = list(
            Choice.objects.filter(
                project_id=self.context["project"],
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

    def __init__(self, **kwargs):
        super().__init__("site", **kwargs)

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
