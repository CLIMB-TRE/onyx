import functools
import operator
from typing import Any
from django.db import models
from django.db.models import F, Q


# TODO: Test constraints


def unique_together(
    model_name: str,
    fields: list[str],
    fields_name: str | None = None,
):
    """
    Creates a unique constraint over the provided `fields`.

    This means that the combination of these fields in a given instance must be unique across all other instances.

    Args:
        model_name: The name of the model (used in naming the constraint).
        fields: The fields to create the constraint over.
        fields_name: The name of the group of fields (used in naming the constraint).

    Returns:
        The constraint.
    """

    if not fields_name:
        fields_name = "_".join(fields)

    return models.UniqueConstraint(
        fields=fields,
        name=f"unique_together_{model_name}_{fields_name}",
    )


def optional_value_group(
    model_name: str,
    fields: list[str],
    fields_name: str | None = None,
):
    """
    Creates a constraint that ensures at least one of the provided `fields` is not null.

    Args:
        model_name: The name of the model (used in naming the constraint).
        fields: The fields to create the constraint over.
        fields_name: The name of the group of fields (used in naming the constraint).

    Returns:
        The constraint.
    """

    # For each field, build a Q object that requires the field is not null
    q_objects = [Q(**{f"{field}__isnull": False}) for field in fields]

    # Reduce the Q objects into a single Q object that requires at least one of the fields is not null
    # This is done by OR-ing the Q objects together
    check = functools.reduce(operator.or_, q_objects)

    if not fields_name:
        fields_name = "_".join(fields)

    return models.CheckConstraint(
        check=check,
        name=f"optional_value_group_{model_name}_{fields_name}",
        violation_error_message=f"At least one of the fields within the group {fields_name} is required.",
    )


def ordering(
    model_name: str,
    fields: tuple[str, str],
    fields_name: str | None = None,
):
    """
    Creates a constraint that ensures the first field is less than or equal to the second field.

    Args:
        model_name: The name of the model (used in naming the constraint).
        fields: The fields to create the constraint over.
        fields_name: The name of the group of fields (used in naming the constraint).

    Returns:
        The constraint.
    """

    # Split the fields tuple into lower and higher
    lower, higher = fields

    # Build a Q object that says either:
    # - One of the two fields is null
    # - The lower field is less than or equal to the higher field
    check = (
        models.Q(**{f"{lower}__isnull": True})
        | models.Q(**{f"{higher}__isnull": True})
        | models.Q(**{f"{lower}__lte": models.F(higher)})
    )

    if not fields_name:
        fields_name = f"{lower}_{higher}"

    return models.CheckConstraint(
        check=check,
        name=f"ordering_{model_name}_{fields_name}",
        violation_error_message=f"The '{lower}' must be less than or equal to '{higher}'.",
    )


def non_futures(
    model_name: str,
    fields: list[str],
    fields_name: str | None = None,
):
    """
    Creates a constraint that ensures that the provided `fields` are not from the future.

    Args:
        model_name: The name of the model (used in naming the constraint).
        fields: The fields to create the constraint over.
        fields_name: The name of the group of fields (used in naming the constraint).

    Returns:
        The constraint.
    """

    # Build a Q object that says (for each field) either:
    # - The field is null
    # - The field's value is less than or equal to the last_modified field
    check = functools.reduce(
        operator.and_,
        [
            Q(**{f"{field}__isnull": True}) | Q(**{f"{field}__lte": F("last_modified")})
            for field in fields
        ],
    )

    if not fields_name:
        fields_name = "_".join(fields)

    return models.CheckConstraint(
        check=check,
        name=f"non_future_{model_name}_{fields_name}",
        violation_error_message=f"At least one of the fields within the group {fields_name} is from the future.",
    )


def conditional_required(
    model_name: str,
    field: str,
    required: list[str],
    required_name: str | None = None,
):
    """
    Creates a constraint that ensures that the `field` can only be not null when all of the `required` fields are not null.

    Args:
        model_name: The name of the model (used in naming the constraint).
        field: The field to create the constraint over.
        required: The fields that are required in order to set the `field`.
        required_name: The name of the group of required fields (used in naming the constraint).

    Returns:
        The constraint.
    """

    # Build a Q object that says all of the required fields are not null
    requirements = functools.reduce(
        operator.and_, [Q(**{f"{req}__isnull": False}) for req in required]
    )

    # Build a Q object that says the field is not null
    condition = Q(**{f"{field}__isnull": False})

    # We have the following:
    # - condition: The field is not null
    # - requirements: All of the required fields are not null
    # We want a Q object that satisfies the following condition:
    # condition IMPLIES requirements
    # This is logically equivalent to:
    # (NOT condition) OR requirements
    check = (~condition) | requirements

    if not required_name:
        required_name = "_".join(required)

    return models.CheckConstraint(
        check=check,
        name=f"conditional_required_{model_name}_{field}_requires_{required_name}",
        violation_error_message=f"All fields within the group {required_name} are required in order to set {field}.",
    )


def conditional_value_required(
    model_name: str,
    field: str,
    value: Any,
    required: list[str],
    required_name: str | None = None,
):
    """
    Creates a constraint that ensures that the `field` can only be set to the `value` when all of the `required` fields are not null.

    Args:
        model_name: The name of the model (used in naming the constraint).
        field: The field to create the constraint over.
        value: The value that the `field` is required to be set to.
        required: The fields that are required in order to set the `field` to the `value`.
        required_name: The name of the group of required fields (used in naming the constraint).

    Returns:
        The constraint.
    """

    # Build a Q object that says all of the required fields are not null
    requirements = functools.reduce(
        operator.and_, [Q(**{f"{req}__isnull": False}) for req in required]
    )

    # Build a Q object that says the field is equal to the value
    condition = Q(**{field: value})

    # We have the following:
    # - condition: The field is equal to the value
    # - requirements: All of the required fields are not null
    # We want a Q object that satisfies the following condition:
    # condition IMPLIES requirements
    # This is logically equivalent to:
    # (NOT condition) OR requirements
    check = (~condition) | requirements

    if not required_name:
        required_name = "_".join(required)

    return models.CheckConstraint(
        check=check,
        name=f"conditional_value_required_{model_name}_{field}_value_requires_{required_name}",
        violation_error_message=f"All fields within the group {required_name} are required in order to set {field} to the value.",
    )
