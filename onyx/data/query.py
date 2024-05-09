from __future__ import annotations
import operator
import functools
from enum import Enum
from typing import Any
from typing_extensions import Annotated
import pydantic
from django.conf import settings
from django.db.models import Q
from rest_framework import exceptions
from utils.functions import pydantic_to_drf_error
from .filters import OnyxFilter
from .fields import FieldHandler
from .types import OnyxLookup


class QuerySymbol(Enum):
    ATOM = "Atom"
    AND = "&"
    OR = "|"
    XOR = "^"
    NOT = "~"


def get_discriminator_value(obj):
    if isinstance(obj, dict):
        key = next(iter(obj.keys()), None)

        try:
            return QuerySymbol(key).value
        except ValueError:
            pass

    return QuerySymbol.ATOM.value


class Atom(pydantic.RootModel):
    """
    The most basic query element.
    """

    root: dict[str, str | int | float | bool | None] = pydantic.Field(
        min_length=1, max_length=1
    )


class AND(pydantic.BaseModel):
    """
    Logical AND operation.
    """

    op: list[Query] = pydantic.Field(
        alias=QuerySymbol.AND.value,
        min_length=1,
        max_length=settings.ONYX_CONFIG["MAX_ITERABLE_INPUT"],
    )
    model_config = pydantic.ConfigDict(extra="forbid")


class OR(pydantic.BaseModel):
    """
    Logical OR operation.
    """

    op: list[Query] = pydantic.Field(
        alias=QuerySymbol.OR.value,
        min_length=1,
        max_length=settings.ONYX_CONFIG["MAX_ITERABLE_INPUT"],
    )
    model_config = pydantic.ConfigDict(extra="forbid")


class XOR(pydantic.BaseModel):
    """
    Logical XOR operation.
    """

    op: list[Query] = pydantic.Field(
        alias=QuerySymbol.XOR.value,
        min_length=1,
        max_length=settings.ONYX_CONFIG["MAX_ITERABLE_INPUT"],
    )
    model_config = pydantic.ConfigDict(extra="forbid")


class NOT(pydantic.BaseModel):
    """
    Logical NOT operation.
    """

    op: Query = pydantic.Field(alias=QuerySymbol.NOT.value)
    model_config = pydantic.ConfigDict(extra="forbid")


class Query(pydantic.RootModel):
    """
    Generic structure for a query: can be an atom or a logical operation.
    """

    root: Annotated[
        Annotated[Atom, pydantic.Tag(QuerySymbol.ATOM.value)]
        | Annotated[AND, pydantic.Tag(QuerySymbol.AND.value)]
        | Annotated[OR, pydantic.Tag(QuerySymbol.OR.value)]
        | Annotated[XOR, pydantic.Tag(QuerySymbol.XOR.value)]
        | Annotated[NOT, pydantic.Tag(QuerySymbol.NOT.value)],
        pydantic.Discriminator(get_discriminator_value),
    ]


class QueryBuilder:
    __slots__ = "data", "field_handler", "onyx_fields", "errors"

    def __init__(self, data: dict[str, Any], handler: FieldHandler) -> None:
        """
        Initialises the QueryBuilder object with the provided data and field handler.

        Args:
            data: The data to build the query from.
            handler: The field handler to use for resolving fields.
        """

        self.field_handler = handler
        self.onyx_fields = []
        self.errors = {}

        try:
            self.data = Query.model_validate(data).model_dump(
                mode="python", by_alias=True
            )
            self.validate_fields(self.data)
            self.validate_field_values()
        except pydantic.ValidationError as e:
            for name, err in pydantic_to_drf_error(e).args[0].items():
                self.errors.setdefault(name, []).extend(err)

    def validate_fields(self, data: dict[str, Any]) -> None:
        """
        Validates the fields in the provided data.

        Args:
            data: The data to validate.
        """

        key, value = next(iter(data.items()))

        if key in {
            QuerySymbol.AND.value,
            QuerySymbol.OR.value,
            QuerySymbol.XOR.value,
        }:
            for k_v in value:
                self.validate_fields(k_v)

        elif key == QuerySymbol.NOT.value:
            self.validate_fields(value)

        else:
            try:
                # Initialise OnyxField object
                # Lookups are allowed for filter fields
                onyx_field = self.field_handler.resolve_field(key, allow_lookup=True)

                # The value is turned into a str for the filterset form.
                # This is what the filterset is built to handle; it attempts to decode these strs and returns errors if it fails.
                # If we don't turn these values into strs, the filterset can crash
                # e.g. If you pass a list, it assumes it is a str, and tries to split by a comma -> ERROR
                onyx_field.value = str(value) if value is not None else ""

                # Replace the data value with the OnyxField object
                data[key] = onyx_field

                # Now append the OnyxField object to the onyx_fields list
                # This is done so that it's easy to modify the OnyxField objects
                # While also preserving the original structure of the query
                self.onyx_fields.append(onyx_field)
            except exceptions.ValidationError as e:
                self.errors.setdefault(key, []).append(e.args[0])

    def validate_field_values(self) -> None:
        """
        Validates the values of the fields in the query data.
        """

        # Each OnyxField object is mapped to a unique key
        onyx_fields_map = {}
        for i, onyx_field in enumerate(self.onyx_fields):
            key = "-".join([str(i), onyx_field.field_path, onyx_field.lookup])
            onyx_fields_map[key] = onyx_field

        # Use a filterset to validate the data
        # Slightly cursed, but it works
        # Until we construct the query, it doesn't matter how fields are related in the query (i.e. AND, OR, etc)
        # All that matters is that the individual fields (and lookups) with their values are valid
        filterset = OnyxFilter(
            onyx_fields_map,
            data={key: onyx_field.value for key, onyx_field in onyx_fields_map.items()},
            queryset=self.field_handler.model.objects.none(),
        )

        if filterset.is_valid():
            # Update the OnyxField objects with their cleaned values
            for key, onyx_field in onyx_fields_map.items():
                onyx_field.value = filterset.form.cleaned_data[key]
        else:
            # If not valid, record the errors
            for key, errors in filterset.errors.items():
                onyx_field = onyx_fields_map[key]

                if onyx_field.lookup:
                    filter_path = f"{onyx_field.field_path}__{onyx_field.lookup}"
                else:
                    filter_path = onyx_field.field_path

                self.errors.setdefault(filter_path, []).extend(errors)

    def is_valid(self) -> bool:
        """
        Returns True if the query data is valid, False otherwise.
        """

        return not self.errors

    def _build(self, data: dict[str, Any]) -> Q:
        """
        Recursively builds a Q object from the provided query data.

        Args:
            data: The data to build the Q object from.

        Returns:
            The Q object built from the provided data.
        """

        key, value = next(iter(data.items()))

        operators = {
            QuerySymbol.AND.value: operator.and_,
            QuerySymbol.OR.value: operator.or_,
            QuerySymbol.XOR.value: operator.xor,
        }

        if key in operators:
            q_objects = [self._build(k_v) for k_v in value]
            return functools.reduce(operators[key], q_objects)

        elif key == QuerySymbol.NOT.value:
            return ~self._build(value)

        else:
            # Base case: 'value' here is an OnyxField object
            # That by this point, should have been cleaned and corrected to work in a query
            # Handle manual overrides for Q objects of certain lookups
            if value.lookup == OnyxLookup.NE.label:
                if value.value is None:
                    return Q(
                        **{f"{value.field_path}__{OnyxLookup.ISNULL.label}": False}
                    )
                else:
                    return ~Q(**{value.field_path: value.value})

            elif value.lookup == OnyxLookup.IN.label and None in value.value:
                values = [v for v in value.value if v is not None]
                return Q(**{f"{value.field_path}__{value.lookup}": values}) | Q(
                    **{f"{value.field_path}__{OnyxLookup.ISNULL.label}": True}
                )

            elif value.lookup == OnyxLookup.NOTIN.label:
                if None in value.value:
                    values = [v for v in value.value if v is not None]
                    return ~(
                        Q(**{f"{value.field_path}__{OnyxLookup.IN.label}": values})
                        | Q(**{f"{value.field_path}__{OnyxLookup.ISNULL.label}": True})
                    )
                else:
                    return ~Q(
                        **{f"{value.field_path}__{OnyxLookup.IN.label}": value.value}
                    )

            elif value.lookup == OnyxLookup.ISNULL.label:
                if value.value:
                    return Q(**{f"{value.field_path}__{value.lookup}": True})
                else:
                    # Using an exclude here causes Django to generate a much more efficient query for relational fields
                    # https://stackoverflow.com/questions/7171041/what-does-it-mean-by-select-1-from-table
                    return ~Q(**{f"{value.field_path}__{value.lookup}": True})

            else:
                if value.lookup:
                    filter_path = f"{value.field_path}__{value.lookup}"
                else:
                    filter_path = value.field_path

                return Q(**{filter_path: value.value})

    def build(self) -> Q:
        """
        Builds a Q object from the provided query data.
        """

        assert not self.errors, "Errors must be resolved before building query"
        return self._build(self.data)
