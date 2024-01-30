import functools
import operator
from django.db import models
from django.db.models import F, Q


# TODO: Test constraints


def unique_together(model_name: str, fields: list[str]):
    """
    Creates a unique constraint over the provided `fields`.

    This means that the combination of these fields in a given instance must be unique across all other instances.

    Args:
        model_name: The name of the model (used in naming the constraint).
        fields: The fields to create the constraint over.

    Returns:
        The constraint.
    """

    return models.UniqueConstraint(
        fields=fields,
        name=f"unique_together_{model_name}_{'_'.join(fields)}",
    )


def optional_value_group(model_name: str, fields: list[str]):
    """
    Creates a constraint that ensures at least one of the provided `fields` is not null.

    Args:
        model_name: The name of the model (used in naming the constraint).
        fields: The fields to create the constraint over.

    Returns:
        The constraint.
    """

    # For each field, build a Q object that requires the field is not null
    q_objects = [Q(**{f"{field}__isnull": False}) for field in fields]

    # Reduce the Q objects into a single Q object that requires at least one of the fields is not null
    # This is done by OR-ing the Q objects together
    check = functools.reduce(operator.or_, q_objects)

    return models.CheckConstraint(
        check=check,
        name=f"optional_value_group_{model_name}_{'_'.join(fields)}",
        violation_error_message="At least one of '"
        + "', '".join(fields)
        + "' is required.",
    )


def ordering(model_name: str, fields: tuple[str, str]):
    """
    Creates a constraint that ensures the first field is less than or equal to the second field.

    Args:
        model_name: The name of the model (used in naming the constraint).
        fields: The fields to create the constraint over.

    Returns:
        The constraint.
    """

    # Split the fields tuple into lower and higher
    lower, higher = fields

    # Build a Q object that requires that either:
    # - One of the two fields is null
    # - The lower field is less than or equal to the higher field
    check = (
        models.Q(**{f"{lower}__isnull": True})
        | models.Q(**{f"{higher}__isnull": True})
        | models.Q(**{f"{lower}__lte": models.F(higher)})
    )

    return models.CheckConstraint(
        check=check,
        name=f"ordering_{model_name}_{lower}_{higher}",
        violation_error_message=f"The '{lower}' must be less than or equal to '{higher}'.",
    )


def non_futures(model_name: str, fields: list[str]):
    """
    Creates a constraint that ensures that the provided `fields` are not from the future.

    Args:
        model_name: The name of the model (used in naming the constraint).
        fields: The fields to create the constraint over.

    Returns:
        The constraint.
    """

    # For each field, build a Q object that requires the field is null or less than or equal to the last_modified field
    q_objects = [
        Q(**{f"{field}__isnull": True}) | Q(**{f"{field}__lte": F("last_modified")})
        for field in fields
    ]

    # Reduce the Q objects into a single Q object that requires all of the fields are not from the future
    # This is done by AND-ing the Q objects together
    check = functools.reduce(
        operator.and_,
        q_objects,
    )

    return models.CheckConstraint(
        check=check,
        name=f"non_future_{model_name}_{'_'.join(fields)}",
        violation_error_message="At least one of '"
        + "', '".join(fields)
        + "' is from the future.",
    )


def conditional_required(model_name: str, field: str, required: list[str]):
    """
    Creates a constraint that ensures that the provided `field` must be null unless all of the `required` fields are not null.

    Args:
        model_name: The name of the model (used in naming the constraint).
        field: The field to create the constraint over.
        required: The fields that are required in order to set the `field`.

    Returns:
        The constraint.
    """

    # For each required field, build a Q object that requires the field is not null
    q_objects = [Q(**{f"{req}__isnull": False}) for req in required]

    # Reduce the Q objects into a single Q object that requires all of the required fields are not null
    requirements = functools.reduce(operator.and_, q_objects)

    # Build a Q object that requires that either:
    # - The field is null
    # - All of the required fields are not null
    check = Q(**{f"{field}__isnull": True}) | requirements

    return models.CheckConstraint(
        check=check,
        name=f"conditional_required_{model_name}_{field}_requires_{'_'.join(required)}",
        violation_error_message="All of '"
        + "', '".join(required)
        + "' are required in order to set "
        + field
        + ".",
    )
