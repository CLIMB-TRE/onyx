from rest_framework import serializers
from rest_framework.fields import empty
from django.utils.translation import gettext_lazy as _
from data.models import Choice
from accounts.models import Site
from utils.functions import get_suggestions


class CharField(serializers.CharField):
    def validate_empty_values(self, data):
        if data is None:
            data = ""

        return super().validate_empty_values(data)

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


class IntegerField(serializers.IntegerField):
    def validate_empty_values(self, data):
        if not str(data).strip():
            data = None

        return super().validate_empty_values(data)

    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")

        return super().to_internal_value(data)


class FloatField(serializers.FloatField):
    def validate_empty_values(self, data):
        if not str(data).strip():
            data = None

        return super().validate_empty_values(data)

    def to_internal_value(self, data):
        if isinstance(data, bool):
            self.fail("invalid")

        return super().to_internal_value(data)


class DateField(serializers.DateField):
    def __init__(self, format: type[empty] | str = empty, input_formats=None, **kwargs):
        super().__init__(
            format,  #  type: ignore
            input_formats=input_formats,
            **kwargs,
        )

    def validate_empty_values(self, data):
        if not str(data).strip():
            data = None

        return super().validate_empty_values(data)


class ChoiceField(serializers.ChoiceField):
    default_error_messages = {"invalid_choice": _("{suggestions}")}

    def __init__(self, field, **kwargs):
        self.field = field
        super().__init__([], **kwargs)

    def validate_empty_values(self, data):
        if data is None:
            data = ""

        return super().validate_empty_values(data)

    def to_internal_value(self, data):
        data = str(data).strip().lower()

        # Check if the choices for this field have been cached in the context
        choices = self.context.setdefault("choices", {}).get(self.field)

        if choices:
            self.choices = choices
        else:
            # If not, fetch the choices from the database
            self.choices = list(
                Choice.objects.filter(
                    project=self.context["project"],
                    field=self.field,
                    is_active=True,
                ).values_list(
                    "choice",
                    flat=True,
                )
            )

            # Cache the choices in the context
            self.context["choices"][self.field] = self.choices

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


class JSONFieldMixin:
    def to_internal_value(self, data):
        data = serializers.JSONField(
            binary=True if isinstance(data, str) else False
        ).to_internal_value(data)

        return super().to_internal_value(data)  # type: ignore


class ArrayField(JSONFieldMixin, serializers.ListField):
    pass


class StructureField(JSONFieldMixin, serializers.DictField):
    pass
