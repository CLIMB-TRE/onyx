from django.db.models import Q, QuerySet
from django.db.models.manager import BaseManager
from accounts.models import User
from .models import ProjectRecord


def init_project_queryset(
    model: type[ProjectRecord],
    user: User,
    fields: list[str],
) -> BaseManager[ProjectRecord]:
    """
    Initialize a QuerySet for a project model based on the user's access to fields.

    Args:
        model: The model to initialize the QuerySet for.
        user: The user to check access for.
        fields: The fields the user has access to.

    Returns:
        A QuerySet for the model with the appropriate filters applied.
    """

    qs = model.objects.select_related()

    if "is_published" not in fields:
        # If the user does not have access to the is_published field, hide unpublished data
        qs = qs.filter(is_published=True)

    if "is_suppressed" not in fields:
        # If the user does not have access to the is_suppressed field, hide suppressed data
        qs = qs.filter(is_suppressed=False)

    if "is_site_restricted" not in fields:
        # If the user does not have access to the is_site_restricted field, hide site-restricted data from other sites
        # TODO: For is_site_restricted to work properly, need to have site stored directly on project record
        # Or have it check the project record's site
        qs = qs.exclude(Q(is_site_restricted=True) & ~Q(user__site=user.site))

    return qs


def prefetch_nested(
    qs: QuerySet,
    fields_dict: dict,
    prefix: str | None = None,
) -> QuerySet:
    """
    For each field in `fields_dict` that contains nested data, apply prefetching to the QuerySet `qs`.

    Args:
        qs: The QuerySet to apply prefetching to.
        fields_dict: A dictionary of fields, where nested fields trigger prefetching.
        prefix: The prefix to use for the fields.

    Returns:
        The QuerySet with prefetching applied.
    """

    for field, nested in fields_dict.items():
        if nested:
            if prefix:
                field = f"{prefix}__{field}"

            qs = qs.prefetch_related(field)
            qs = prefetch_nested(
                qs=qs,
                fields_dict=nested,
                prefix=field,
            )

    return qs
