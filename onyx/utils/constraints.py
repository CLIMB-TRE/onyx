import functools
import operator
from datetime import datetime
from django.db import models
from django.db.models import Q


# TODO: Test constraints


def unique_together(model_name: str, fields: list[str]):
    return models.UniqueConstraint(
        fields=fields,
        name=f"unique_together_{model_name}_{'_'.join(fields)}",
    )


def optional_value_group(model_name: str, fields: list[str]):
    return models.CheckConstraint(
        check=functools.reduce(
            operator.or_, [Q(**{f"{field}__isnull": False}) for field in fields]
        ),
        name=f"optional_value_group_{model_name}_{'_'.join(fields)}",
        violation_error_message="At least one of '"
        + "', '".join(fields)
        + "' is required.",
    )


def ordering(model_name: str, fields: tuple[str, str]):
    lower, higher = fields
    return models.CheckConstraint(
        check=(
            models.Q(**{f"{lower}__isnull": True})
            | models.Q(**{f"{higher}__isnull": True})
            | models.Q(**{f"{lower}__lte": models.F(higher)})
        ),
        name=f"ordering_{model_name}_{lower}_{higher}",
        violation_error_message=f"The '{lower}' must be less than or equal to '{higher}'.",
    )


# TODO: BROKEN
# The reason it keeps self adding/removing is because it changes each time the date changes
# So it's not a static constraint
# Could be fixed by doing a comparison to e.g. the last_modified date
def non_futures(model_name: str, fields: list[str]):
    return models.CheckConstraint(
        check=functools.reduce(
            operator.and_,
            [
                Q(**{f"{field}__isnull": True})
                | ~Q(**{f"{field}__gt": datetime.now().date()})
                for field in fields
            ],
        ),
        name=f"non_future_{model_name}_{'_'.join(fields)}",
        violation_error_message="At least one of '"
        + "', '".join(fields)
        + "' is from the future.",
    )


def conditional_required(model_name: str, field: str, required: list[str]):
    return models.CheckConstraint(
        check=Q(**{f"{field}__isnull": True})
        | functools.reduce(
            operator.and_, [Q(**{f"{req}__isnull": False}) for req in required]
        ),
        name=f"conditional_required_{model_name}_{field}_requires_{'_'.join(required)}",
        violation_error_message="All of '"
        + "', '".join(required)
        + "' are required in order to set "
        + field
        + ".",
    )
