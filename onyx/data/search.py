from django.db.models import Q


def build_search(search_str: str, search_fields: list[str]) -> Q:
    """
    Build a Q object that checks for presence of the user's search against the search fields.

    Args:
        search_str: The user's search string.
        search_fields: The fields to search against.

    Returns:
        A Q object representing the search.
    """

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
