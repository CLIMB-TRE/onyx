from __future__ import annotations
import operator
import functools
from typing import Dict, List, Any
from django.db.models import Q, Model
from rest_framework import exceptions
from pydantic import RootModel, BaseModel, Field, ValidationError, ConfigDict
from .filters import OnyxFilter
from .fields import OnyxField


from typing_extensions import Annotated

from pydantic import BaseModel, ValidationError
from pydantic.functional_validators import AfterValidator


def check_length(v: dict) -> dict:
    if len(v) != 1:
        raise ValueError(f"atom is not a single key-value pair")
    return v


class Atom(RootModel):
    root: Annotated[dict[str, str], AfterValidator(check_length)]
    model_config = ConfigDict(coerce_numbers_to_str=True)


class AND(BaseModel):
    op: list[Atom | AND | OR | NOT | XOR] = Field(alias="&")


class OR(BaseModel):
    op: list[Atom | AND | OR | NOT | XOR] = Field(alias="|")


class XOR(BaseModel):
    op: list[Atom | AND | OR | NOT | XOR] = Field(alias="^")


class NOT(BaseModel):
    op: Atom | AND | OR | NOT | XOR = Field(alias="~")


class Query(RootModel):
    root: Atom | AND | OR | NOT | XOR


class QueryAtom:
    """
    Class for representing the most basic component of a query; a single key-value pair.
    """

    __slots__ = "key", "value", "exclude", "default"

    def __init__(self, key, value, exclude=False, default=None):
        self.key = key
        self.value = value
        self.exclude = exclude
        self.default = default


# TODO: Improve validation or find better ways e.g. JSON Schema?
def validate_data(func):
    def wrapped(data, *args, **kwargs):
        if not isinstance(data, dict):
            raise exceptions.ValidationError(
                {
                    "detail": f"Expected dictionary when parsing query but received type: {type(data)}"
                }
            )

        if len(data.items()) != 1:
            raise exceptions.ValidationError(
                {"detail": "Dictionary within query is not a single key-value pair"}
            )

        key, value = next(iter(data.items()))

        if key in {"&", "|", "^"}:
            if not isinstance(value, list):
                raise exceptions.ValidationError(
                    {
                        "detail": f"Expected list when parsing query but received type: {type(value)}"
                    }
                )
            if len(value) < 1:
                raise exceptions.ValidationError(
                    {"detail": "List within query must have at least one item"}
                )

        return func(data, *args, **kwargs)

    return wrapped


# @validate_data
def make_atoms(data: Dict[str, Any]) -> List[QueryAtom]:
    """
    Traverses the provided `data` and replaces request values with `QueryAtom` objects.
    Returns a list of these `QueryAtom` objects.
    """

    try:
        Query.model_validate(data)
    except ValidationError as e:
        errors = {}

        for error in e.errors(
            include_url=False, include_context=False, include_input=False
        ):
            if not error["loc"]:
                errors.setdefault("non_field_errors", []).append(error["msg"])
            else:
                errors.setdefault(error["loc"][0], []).append(error["msg"])

        for name, errs in errors.items():
            errors[name] = list(set(errs))

        raise exceptions.ValidationError(errors)

    key, value = next(iter(data.items()))

    if key in {"&", "|", "^"}:
        atoms = [make_atoms(k_v) for k_v in value]
        return functools.reduce(operator.add, atoms)

    elif key == "~":
        return make_atoms(value)

    else:
        # Initialise QueryAtom object
        # The value is turned into a str for the filterset form.
        # This is what the filterset is built to handle; it attempts to decode these strs and returns errors if it fails.
        # If we don't turn these values into strs, the filterset can crash
        # e.g. If you pass a list, it assumes it is a str, and tries to split by a comma -> ERROR
        atom = QueryAtom(key, str(value) if value is not None else "")

        # Replace the data value with the QueryAtom object
        data[key] = atom

        # Now return the QueryAtom object
        # This is done so that it's easy to modify the QueryAtom objects
        # While also preserving the original structure of the query
        return [atom]


# @validate_data
def make_query(data: Dict[str, Any]) -> Q:
    """
    Traverses the provided `data` and forms the corresponding Q object.
    """

    key, value = next(iter(data.items()))
    operators = {"&": operator.and_, "|": operator.or_, "^": operator.xor}

    if key in operators:
        q_objects = [make_query(k_v) for k_v in value]
        return functools.reduce(operators[key], q_objects)

    elif key == "~":
        return ~make_query(value)

    else:
        # Base case: a QueryAtom to filter on
        # 'value' here is a QueryAtom object
        # That by this point, should have been cleaned and corrected to work in a query
        if value.default:
            q = value.default
        else:
            q = Q(**{value.key: value.value})

        if value.exclude:
            q = ~q
        return q


def validate_atoms(
    model: type[Model],
    atoms: List[QueryAtom],
    onyx_fields: Dict[str, OnyxField],
) -> None:
    """
    Use the `OnyxFilter` to validate and clean the provided list of `atoms`.
    """

    # Construct a list of dictionaries from the atoms
    # Each of these dictionaries will be passed to the OnyxFilter
    # The OnyxFilter is then used to validate and clean the inputs
    # Until we construct the query, it doesn't matter how fields are related in the query (i.e. AND, OR, etc)
    # All that matters is that the individual fields (and lookups) with their values are valid
    layers = [{}]

    for atom in atoms:
        # Place the QueryAtom in the first dictionary where the key is not present
        # If we reach the end with no placement, create a new dictionary and add it in there
        for layer in layers:
            if atom.key not in layer:
                layer[atom.key] = atom
                break
        else:
            layers.append({atom.key: atom})

    # Use a filterset, applied to each layer, to validate the data
    # Slightly cursed, but it works
    errors = {}
    for layer in layers:
        fs = OnyxFilter(
            onyx_fields,
            data={k: v.value for k, v in layer.items()},
            queryset=model.objects.none(),
        )

        if fs.is_valid():
            # Update the QueryAtom objects with their cleaned values
            for k, atom in layer.items():
                atom.value = fs.form.cleaned_data[k]

                # Handle manual overrides for Q objects of certain lookups
                if onyx_fields[k].lookup == "ne":
                    if atom.value is None:
                        atom.key = f"{onyx_fields[k].field_path}__isnull"
                        atom.value = False
                    else:
                        atom.key = onyx_fields[k].field_path
                        atom.exclude = True

                elif onyx_fields[k].lookup == "in":
                    if None in atom.value:
                        atom.value = [v for v in atom.value if v is not None]
                        atom.default = Q(**{atom.key: atom.value}) | Q(
                            **{f"{onyx_fields[k].field_path}__isnull": True}
                        )

                elif onyx_fields[k].lookup == "notin":
                    atom.key = f"{onyx_fields[k].field_path}__in"
                    atom.exclude = True

                    if None in atom.value:
                        atom.value = [v for v in atom.value if v is not None]
                        atom.default = Q(**{atom.key: atom.value}) | Q(
                            **{f"{onyx_fields[k].field_path}__isnull": True}
                        )

        else:
            # If not valid, record the errors
            for field_name, field_errors in fs.errors.items():
                errors.setdefault(field_name, []).extend(field_errors)

    if errors:
        raise exceptions.ValidationError(errors)
