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

    field_set = set(fields)
    qs = model.objects.select_related()

    if "is_published" not in field_set:
        # If the user does not have access to the is_published field, exclude unpublished data
        qs = qs.exclude(is_published=False)

    if "is_suppressed" not in field_set:
        # If the user does not have access to the is_suppressed field, exclude suppressed data
        qs = qs.exclude(is_suppressed=True)

    if "is_site_restricted" not in field_set:
        if "site" in set(f.name for f in model._meta.get_fields()):
            # If the user does not have access to the is_site_restricted field,
            # exclude site-restricted data from other sites
            qs = qs.exclude(
                Q(is_site_restricted=True) & ~Q(site__iexact=user.site.code)
            )
        else:
            # If the user does not have access to the is_site_restricted field and
            # the model does not have a site field, exclude any site-restricted data
            qs = qs.exclude(is_site_restricted=True)

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
