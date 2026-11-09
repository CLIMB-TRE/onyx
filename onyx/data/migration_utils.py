from django.db import models
from django.db.models import OuterRef, Subquery
from django.db.models.functions import Cast, Coalesce


def backfill_published_timestamp(model, history_model):
    """
    Backfill `published_timestamp` for objects of `model` that have a `published_date`.

    The timestamp is taken from the earliest historical record where `published_date` was set.
    If no such historical record exists, it falls back to midnight (UTC) on the `published_date`.

    Only the live table is updated; historical records are left as they are.

    NOTE: This function is used by migrations. Do not modify its behaviour.
    """

    first_published = (
        history_model.objects.filter(
            id=OuterRef("id"),
            published_date__isnull=False,
        )
        .order_by("history_date")
        .values("history_date")[:1]
    )

    model.objects.filter(
        published_date__isnull=False,
        published_timestamp__isnull=True,
    ).update(
        published_timestamp=Coalesce(
            Subquery(first_published),
            Cast("published_date", models.DateTimeField()),
        )
    )
