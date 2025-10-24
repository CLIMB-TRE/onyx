import functools
import hashlib
import operator
from enum import Enum
from typing import Any
from django.db import models
from django.db.models import F, Q


# TODO: Test constraints


class ConstraintCodes(Enum):
    UNIQUE_TOGETHER = "ut"
    OPTIONAL_VALUE_GROUP = "ovg"
    ORDERING = "ord"
    NON_FUTURES = "nf"
    CONDITIONAL_REQUIRED = "cr"
    CONDITIONAL_VALUE_REQUIRED = "cvr"
    CONDITIONAL_VALUE_OPTIONAL_VALUE_GROUP = "cvo"

    def __init__(self, label: str) -> None:
        self.label = label


def generate_constraint_name(code: str, fields: list[str]) -> str:
    """
    Generates a unique name for a constraint based on the provided `code` and `fields`.

    Args:
        code: The constraint code.
        fields: List of fields involved.

    Returns:
        The generated name.
    """

    fields_identifier = "_".join(fields)
    constraint_identifier = "_".join(
        ["%(app_label)s", "%(class)s", code, fields_identifier]
    )
    hasher = hashlib.sha256()
    hasher.update(constraint_identifier.encode("utf-8"))
    hash = hasher.hexdigest()

    # The layout of the constraint name follows the structure of Django's index names
    return f"%(app_label)s_%(class)s_{fields_identifier[:7]}_{hash[:6]}_{code}"


def unique_together(fields: list[str]):
    """
    Creates a unique constraint over the provided `fields`.

    This means that the combination of these fields in a given instance must be unique across all other instances.

    Args:
        fields: The fields to create the constraint over.

    Returns:
        The constraint.
    """

    return models.UniqueConstraint(
        fields=fields,
        name=generate_constraint_name(
            code=ConstraintCodes.UNIQUE_TOGETHER.value,
            fields=fields,
        ),
    )


def optional_value_group(fields: list[str]):
    """
    Creates a constraint that ensures at least one of the provided `fields` is not null.

    Args:
        fields: The fields to create the constraint over.

    Returns:
        The constraint.
    """

    # Build a Q object that says at least one of the fields is not null
    # This is done by OR-ing the Q objects together
    check = functools.reduce(
        operator.or_, [Q(**{f"{field}__isnull": False}) for field in fields]
    )

    return models.CheckConstraint(
        check=check,
        name=generate_constraint_name(
            code=ConstraintCodes.OPTIONAL_VALUE_GROUP.value,
            fields=fields,
        ),
        violation_error_message=f"At least one of {', '.join(fields)} is required.",
    )


def ordering(fields: tuple[str, str]):
    """
    Creates a constraint that ensures the first field is less than or equal to the second field.

    Args:
        fields: The fields to create the constraint over.

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

    return models.CheckConstraint(
        check=check,
        name=generate_constraint_name(
            code=ConstraintCodes.ORDERING.value,
            fields=list(fields),
        ),
        violation_error_message=f"The {lower} must be less than or equal to {higher}.",
    )


def non_futures(fields: list[str]):
    """
    Creates a constraint that ensures that the provided `fields` are not from the future.

    Args:
        fields: The fields to create the constraint over.

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

    return models.CheckConstraint(
        check=check,
        name=generate_constraint_name(
            code=ConstraintCodes.NON_FUTURES.value,
            fields=fields,
        ),
        violation_error_message=f"At least one of {', '.join(fields)} is from the future.",
    )


def conditional_required(field: str, required: list[str]):
    """
    Creates a constraint that ensures that the `field` can only be not null when all of the `required` fields are not null.

    Args:
        field: The field to create the constraint over.
        required: The fields that are required in order to set the `field`.

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

    return models.CheckConstraint(
        check=check,
        name=generate_constraint_name(
            code=ConstraintCodes.CONDITIONAL_REQUIRED.value,
            fields=[field] + required,
        ),
        violation_error_message=f"Each of {', '.join(required)} are required in order to set {field}.",
    )


def conditional_value_required(field: str, value: Any, required: list[str]):
    """
    Creates a constraint that ensures that the `field` can only be set to the `value` when all of the `required` fields are not null.

    Args:
        field: The field to create the constraint over.
        value: The value that the `field` is required to be set to.
        required: The fields that are required in order to set the `field` to the `value`.

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

    return models.CheckConstraint(
        check=check,
        name=generate_constraint_name(
            code=ConstraintCodes.CONDITIONAL_VALUE_REQUIRED.value,
            fields=[field] + required + [str(value).strip().lower()],
        ),
        violation_error_message=f"Each of {', '.join(required)} are required in order to set {field} to the value.",
    )


def conditional_value_optional_value_group(field: str, value: Any, optional: list[str]):
    """
    Creates a constraint that ensures that the `field` can only be set to the `value` when at least one of the `optional` fields are not null.

    Args:
        field: The field to create the constraint over.
        value: The value that the `field` is required to be set to.
        optional: The fields where at least one is required in order to set the `field` to the `value`.

    Returns:
        The constraint.
    """

    # Build a Q object that says at least one of the required fields is not null
    requirements = functools.reduce(
        operator.or_,
        [Q(**{f"{field}__isnull": False}) for field in optional],
    )

    # Build a Q object that says the field is equal to the value
    condition = Q(**{field: value})

    # We have the following:
    # - condition: The field is equal to the value
    # - requirements: At least one of the optional fields are not null
    # We want a Q object that satisfies the following condition:
    # condition IMPLIES requirements
    # This is logically equivalent to:
    # (NOT condition) OR requirements
    check = (~condition) | requirements

    return models.CheckConstraint(
        check=check,
        name=generate_constraint_name(
            code=ConstraintCodes.CONDITIONAL_VALUE_OPTIONAL_VALUE_GROUP.value,
            fields=[field] + optional + [str(value).strip().lower()],
        ),
        violation_error_message=f"At least one of {', '.join(optional)} are required in order to set {field} to the value.",
    )
