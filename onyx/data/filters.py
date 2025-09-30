import json
from datetime import datetime
from django import forms
from django.core.exceptions import ValidationError
from rest_framework.serializers import BooleanField
from django_filters import rest_framework as filters, fields as filter_fields
from utils.functions import get_suggestions, strtobool
from .types import OnyxType
from .fields import OnyxField


class StrictFieldMixin:
    def clean(self, value):
        value = super().clean(value)  #  type: ignore

        if value is None:
            raise ValidationError("Value cannot be null.")

        return value


class StrictFieldListMixin:
    def clean(self, value):
        value = super().clean(value)  #  type: ignore
        assert isinstance(value, list)

        if not value or None in value:
            raise ValidationError("Value cannot be null.")

        return value


class BaseInField(filter_fields.BaseCSVField):
    def clean(self, value):
        value = super().clean(value)
        assert isinstance(value, list)

        if not value:
            value.append(None)

        return value


class StrictBaseInField(StrictFieldListMixin, BaseInField):
    pass


class BaseInFilter(filters.BaseInFilter):
    base_field_class = BaseInField


class StrictBaseInFilter(BaseInFilter):
    base_field_class = StrictBaseInField


class BaseRangeField(StrictFieldListMixin, filter_fields.BaseRangeField):
    pass


class BaseRangeFilter(filters.BaseRangeFilter):
    base_field_class = BaseRangeField


class CharInField(filter_fields.BaseCSVField):
    def clean(self, value):
        value = super().clean(value)
        assert isinstance(value, list)

        if not value:
            value.append("")

        return value


class CharInFilter(BaseInFilter, filters.CharFilter):
    base_field_class = CharInField


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


class ChoiceInFilter(BaseInFilter, ChoiceFilter):
    base_field_class = CharInField


class NumberFieldForm(forms.DecimalField):
    def clean(self, value):
        if not str(value).strip():
            value = None

        return super().clean(value)


class StrictNumberFieldForm(StrictFieldMixin, NumberFieldForm):
    pass


class NumberFilter(filters.NumberFilter):
    field_class = NumberFieldForm


class StrictNumberFilter(NumberFilter):
    field_class = StrictNumberFieldForm


class NumberInFilter(BaseInFilter, NumberFilter):
    pass


class StrictNumberInFilter(StrictBaseInFilter, StrictNumberFilter):
    pass


class NumberRangeFilter(BaseRangeFilter, StrictNumberFilter):
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

        if not str(value).strip():
            value = None

        return super().clean(value)


class StrictDateFieldForm(StrictFieldMixin, DateFieldForm):
    pass


class DateFilter(filters.Filter):
    field_class = DateFieldForm


class StrictDateFilter(DateFilter):
    field_class = StrictDateFieldForm


class DateInFilter(BaseInFilter, DateFilter):
    pass


class DateRangeFilter(BaseRangeFilter, StrictDateFilter):
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

        if not str(value).strip():
            value = None

        return super().clean(value)


class StrictDateTimeFieldForm(StrictFieldMixin, DateTimeFieldForm):
    pass


class DateTimeFilter(filters.Filter):
    field_class = DateTimeFieldForm


class StrictDateTimeFilter(DateTimeFilter):
    field_class = StrictDateTimeFieldForm


class DateTimeInFilter(BaseInFilter, DateTimeFilter):
    pass


class DateTimeRangeFilter(BaseRangeFilter, StrictDateTimeFilter):
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


class BooleanInFilter(BaseInFilter, BooleanFilter):
    pass


class StrictBooleanForm(StrictFieldMixin, BooleanFieldForm):
    pass


class StrictBooleanFilter(BooleanFilter):
    field_class = StrictBooleanForm


class StructureFieldForm(forms.CharField):
    def clean(self, value):
        value = super().clean(value)

        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            raise ValidationError("Value must be a valid JSON object.")

        return value


class StrictStructureFieldForm(StrictFieldMixin, StructureFieldForm):
    pass


class StructureFilter(filters.Filter):
    field_class = StructureFieldForm


class StrictStructureFilter(StructureFilter):
    field_class = StrictStructureFieldForm


# Mappings from field type + lookup to filter
FILTERS = {
    OnyxType.ID: {lookup: filters.CharFilter for lookup in OnyxType.ID.lookups}
    | {
        "in": CharInFilter,
        "notin": CharInFilter,
        "length": StrictNumberFilter,
        "length__in": StrictNumberInFilter,
        "length__range": NumberRangeFilter,
        "isnull": StrictBooleanFilter,
    },
    OnyxType.TEXT: {lookup: filters.CharFilter for lookup in OnyxType.TEXT.lookups}
    | {
        "in": CharInFilter,
        "notin": CharInFilter,
        "length": StrictNumberFilter,
        "length__in": StrictNumberInFilter,
        "length__range": NumberRangeFilter,
        "isnull": StrictBooleanFilter,
    },
    OnyxType.CHOICE: {lookup: ChoiceFilter for lookup in OnyxType.CHOICE.lookups}
    | {
        "in": ChoiceInFilter,
        "notin": ChoiceInFilter,
        "isnull": StrictBooleanFilter,
    },
    OnyxType.INTEGER: {lookup: NumberFilter for lookup in OnyxType.INTEGER.lookups}
    | {
        "in": NumberInFilter,
        "notin": NumberInFilter,
        "lt": StrictNumberFilter,
        "lte": StrictNumberFilter,
        "gt": StrictNumberFilter,
        "gte": StrictNumberFilter,
        "range": NumberRangeFilter,
        "isnull": StrictBooleanFilter,
    },
    OnyxType.DECIMAL: {lookup: NumberFilter for lookup in OnyxType.DECIMAL.lookups}
    | {
        "in": NumberInFilter,
        "notin": NumberInFilter,
        "lt": StrictNumberFilter,
        "lte": StrictNumberFilter,
        "gt": StrictNumberFilter,
        "gte": StrictNumberFilter,
        "range": NumberRangeFilter,
        "isnull": StrictBooleanFilter,
    },
    OnyxType.DATE: {lookup: DateFilter for lookup in OnyxType.DATE.lookups}
    | {
        "in": DateInFilter,
        "notin": DateInFilter,
        "lt": StrictDateFilter,
        "lte": StrictDateFilter,
        "gt": StrictDateFilter,
        "gte": StrictDateFilter,
        "range": DateRangeFilter,
        "iso_year": StrictNumberFilter,
        "iso_year__in": StrictNumberInFilter,
        "iso_year__range": NumberRangeFilter,
        "week": StrictNumberFilter,
        "week__in": StrictNumberInFilter,
        "week__range": NumberRangeFilter,
        "isnull": StrictBooleanFilter,
    },
    OnyxType.DATETIME: {lookup: DateTimeFilter for lookup in OnyxType.DATETIME.lookups}
    | {
        "in": DateTimeInFilter,
        "notin": DateTimeInFilter,
        "lt": StrictDateTimeFilter,
        "lte": StrictDateTimeFilter,
        "gt": StrictDateTimeFilter,
        "gte": StrictDateTimeFilter,
        "range": DateTimeRangeFilter,
        "iso_year": StrictNumberFilter,
        "iso_year__in": StrictNumberInFilter,
        "iso_year__range": NumberRangeFilter,
        "week": StrictNumberFilter,
        "week__in": StrictNumberInFilter,
        "week__range": NumberRangeFilter,
        "isnull": StrictBooleanFilter,
    },
    OnyxType.BOOLEAN: {lookup: BooleanFilter for lookup in OnyxType.BOOLEAN.lookups}
    | {
        "in": BooleanInFilter,
        "notin": BooleanInFilter,
        "isnull": StrictBooleanFilter,
    },
    OnyxType.RELATION: {
        "isnull": StrictBooleanFilter,
    },
    OnyxType.ARRAY: {
        OnyxType.TEXT: {lookup: CharInFilter for lookup in OnyxType.ARRAY.lookups}
        | {
            "length": StrictNumberFilter,
            "length__in": StrictNumberInFilter,
            "length__range": NumberRangeFilter,
            "isnull": StrictBooleanFilter,
        },
        OnyxType.INTEGER: {lookup: NumberInFilter for lookup in OnyxType.ARRAY.lookups}
        | {
            "length": StrictNumberFilter,
            "length__in": StrictNumberInFilter,
            "length__range": NumberRangeFilter,
            "isnull": StrictBooleanFilter,
        },
    },
    OnyxType.STRUCTURE: {
        lookup: StructureFilter for lookup in OnyxType.STRUCTURE.lookups
    }
    | {
        "contains": StrictStructureFilter,
        "contained_by": StrictStructureFilter,
        "has_key": filters.CharFilter,
        "has_keys": CharInFilter,
        "has_any_keys": CharInFilter,
        "isnull": StrictBooleanFilter,
    },
    OnyxType.IDENTIFIERS: {
        "isnull": StrictBooleanFilter,
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
            if onyx_field.onyx_type == OnyxType.ARRAY:
                base_onyx_field = onyx_field.base_onyx_field
                assert base_onyx_field is not None
                filter = FILTERS[onyx_field.onyx_type][base_onyx_field.onyx_type][
                    onyx_field.lookup
                ]
            else:
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
