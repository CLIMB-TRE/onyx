from django.db.models import Q
from .fields import OnyxField, OnyxType


def build_search(search_str: str, onyx_fields: dict[str, OnyxField]) -> Q:
    """
    Build a Q object that checks for presence of the user's search against text and choice fields.

    Args:
        search_str: The user's search string.
        onyx_fields: A dictionary of field names to OnyxField objects. Only text and choice fields can be searched.

    Returns:
        A Q object representing the search.
    """

    # Get the fields to search over
    search_fields = [
        field
        for field, onyx_field in onyx_fields.items()
        if onyx_field.onyx_type == OnyxType.TEXT
        or onyx_field.onyx_type == OnyxType.CHOICE
    ]

    # If there are no search fields, return a Q object that matches nothing
    if not search_fields:
        return Q(pk__in=[])

    # Split the search string into individual words
    words = []
    for word in search_str.split():
        w = word.strip().strip("'").strip('"').strip()
        if w:
            words.append(w)

    # Form the Q object for the search
    search = Q()
    for word in words:
        s = Q()
        for field in search_fields:
            if field == "site":
                s |= Q(**{f"{field}__code__icontains": word})
            else:
                s |= Q(**{f"{field}__icontains": word})
        search &= s

    # Return the search object
    return search
