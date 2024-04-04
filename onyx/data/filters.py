import re
from datetime import datetime
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from rest_framework.serializers import BooleanField
from django_filters import rest_framework as filters, fields as filter_fields
from utils.functions import get_suggestions, strtobool
from .types import OnyxType
from .fields import OnyxField


# TODO: Reject None values within 'in' filter


class BaseRangeField(filter_fields.BaseRangeField):
    def clean(self, value):
        value = super(filter_fields.BaseRangeField, self).clean(value)

        assert value is None or isinstance(value, list)

        if not value or len(value) != 2 or any(v is None for v in value):
            raise forms.ValidationError(
                self.error_messages["invalid_values"], code="invalid_values"
            )

        return value


class BaseRangeFilter(filters.BaseRangeFilter):
    base_field_class = BaseRangeField


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    pass


class RegexForm(forms.CharField):
    def validate(self, value):
        super().validate(value)
        try:
            re.compile(value)
        except re.error as e:
            raise ValidationError(f"Invalid pattern: {e}")


class RegexFilter(filters.Filter):
    field_class = RegexForm


class ChoiceFieldMixin:
    def clean(self, value):
        self.choice_map = {
            choice.lower().strip(): choice
            for choice, _ in self.choices  #  type: ignore
        }

        if isinstance(value, str):
            value = value.strip()
            value_key = value.lower()

            if value_key in self.choice_map:
                value = self.choice_map[value_key]

        return super().clean(value)  #  type: ignore

    def validate(self, value):
        super(forms.ChoiceField, self).validate(value)  #  type: ignore

        if value and not self.valid_value(value):  #  type: ignore
            choices = [str(x) for (_, x) in self.choices]  #  type: ignore
            suggestions = get_suggestions(
                value,
                options=choices,
                n=1,
                message_prefix="Select a valid choice.",
            )

            raise ValidationError(suggestions)


class ChoiceFieldForm(ChoiceFieldMixin, forms.ChoiceField):
    pass


class ChoiceFilter(filters.Filter):
    field_class = ChoiceFieldForm


class ChoiceInFilter(filters.BaseInFilter, ChoiceFilter):
    pass


class NumberInFilter(filters.BaseInFilter, filters.NumberFilter):
    pass


class NumberRangeFilter(BaseRangeFilter, filters.NumberFilter):
    pass


class DateFieldForm(forms.DateField):
    def __init__(self, **kwargs):
        kwargs["input_formats"] = [
            "%Y-%m",
            "%Y-%m-%d",
        ]
        super().__init__(**kwargs)

    def clean(self, value):
        if isinstance(value, str) and value.strip().lower() == "today":
            value = datetime.now().date()

        return super().clean(value)


class DateFilter(filters.Filter):
    field_class = DateFieldForm


class DateInFilter(filters.BaseInFilter, DateFilter):
    pass


class DateRangeFilter(BaseRangeFilter, DateFilter):
    pass


class DateTimeFieldForm(forms.DateTimeField):
    def __init__(self, **kwargs):
        kwargs["input_formats"] = [
            "%Y-%m",
            "%Y-%m-%d",
            "%Y-%m-%d %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M:%S.%f",
        ]
        super().__init__(**kwargs)

    def clean(self, value):
        if isinstance(value, str) and value.strip().lower() == "today":
            value = datetime.now()

        return super().clean(value)


class DateTimeFilter(filters.Filter):
    field_class = DateTimeFieldForm


class DateTimeInFilter(filters.BaseInFilter, DateTimeFilter):
    pass


class DateTimeRangeFilter(BaseRangeFilter, DateTimeFilter):
    pass


# Boolean choices in correct format for TypedChoiceField
BOOLEAN_CHOICES = [
    (choice, choice)
    for choice in {
        str(value).lower()
        for value in BooleanField.TRUE_VALUES | BooleanField.FALSE_VALUES
    }
]


class BooleanFieldForm(ChoiceFieldMixin, forms.TypedChoiceField):
    def __init__(self, **kwargs):
        kwargs["choices"] = BOOLEAN_CHOICES
        kwargs["coerce"] = lambda x: strtobool(x)
        kwargs["empty_value"] = None
        super().__init__(**kwargs)


class BooleanFilter(filters.TypedChoiceFilter):
    field_class = BooleanFieldForm


class BooleanInFilter(filters.BaseInFilter, BooleanFilter):
    pass


class IsNullForm(BooleanFieldForm):
    def clean(self, value):
        value = super().clean(value)
        if value not in [True, False]:
            raise ValidationError(f"Value must be True or False.")

        return value


class IsNullFilter(BooleanFilter):
    field_class = IsNullForm


# Mappings from field type + lookup to filter
FILTERS = {
    OnyxType.TEXT: {lookup: filters.CharFilter for lookup in OnyxType.TEXT.lookups}
    | {
        "in": CharInFilter,
        "notin": CharInFilter,
        "regex": RegexFilter,
        "iregex": RegexFilter,
        "length": filters.NumberFilter,
        "length__in": NumberInFilter,
        "length__range": NumberRangeFilter,
        "isnull": IsNullFilter,
    },
    OnyxType.CHOICE: {lookup: ChoiceFilter for lookup in OnyxType.CHOICE.lookups}
    | {
        "in": ChoiceInFilter,
        "notin": ChoiceInFilter,
        "isnull": IsNullFilter,
    },
    OnyxType.INTEGER: {
        lookup: filters.NumberFilter for lookup in OnyxType.INTEGER.lookups
    }
    | {
        "in": NumberInFilter,
        "notin": NumberInFilter,
        "range": NumberRangeFilter,
        "isnull": IsNullFilter,
    },
    OnyxType.DECIMAL: {
        lookup: filters.NumberFilter for lookup in OnyxType.DECIMAL.lookups
    }
    | {
        "in": NumberInFilter,
        "notin": NumberInFilter,
        "range": NumberRangeFilter,
        "isnull": IsNullFilter,
    },
    OnyxType.DATE: {lookup: DateFilter for lookup in OnyxType.DATE.lookups}
    | {
        "in": DateInFilter,
        "notin": DateInFilter,
        "range": DateRangeFilter,
        "iso_year": filters.NumberFilter,
        "iso_year__in": NumberInFilter,
        "iso_year__range": NumberRangeFilter,
        "week": filters.NumberFilter,
        "week__in": NumberInFilter,
        "week__range": NumberRangeFilter,
        "isnull": IsNullFilter,
    },
    OnyxType.DATETIME: {lookup: DateTimeFilter for lookup in OnyxType.DATETIME.lookups}
    | {
        "in": DateTimeInFilter,
        "notin": DateTimeInFilter,
        "range": DateTimeRangeFilter,
        "iso_year": filters.NumberFilter,
        "iso_year__in": NumberInFilter,
        "iso_year__range": NumberRangeFilter,
        "week": filters.NumberFilter,
        "week__in": NumberInFilter,
        "week__range": NumberRangeFilter,
        "isnull": IsNullFilter,
    },
    OnyxType.BOOLEAN: {lookup: BooleanFilter for lookup in OnyxType.BOOLEAN.lookups}
    | {
        "in": BooleanInFilter,
        "notin": BooleanInFilter,
        "isnull": IsNullFilter,
    },
    OnyxType.RELATION: {
        "isnull": IsNullFilter,
    },
}


class OnyxFilter(filters.FilterSet):
    def __init__(self, onyx_fields: dict[str, OnyxField], *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Constructing the filterset dynamically enables:
        # Checking whether the provided field_path and lookup can be used together
        # Validating the values provided by the user for the fields
        # Returning cleaned values from user inputs, using the filterset's underlying form
        for field_name, onyx_field in onyx_fields.items():
            filter = FILTERS[onyx_field.onyx_type][onyx_field.lookup]

            if onyx_field.onyx_type == OnyxType.CHOICE:
                choices = [(x, x) for x in onyx_field.choices]
                self.filters[field_name] = filter(
                    field_name=onyx_field.field_path,
                    choices=choices,
                    lookup_expr=onyx_field.lookup,
                )
            else:
                self.filters[field_name] = filter(
                    field_name=onyx_field.field_path,
                    lookup_expr=onyx_field.lookup,
                )
