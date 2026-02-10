from datetime import datetime
from django.db.models import Q
from .fields import OnyxField, OnyxType


def get_search_terms(search_str: str) -> list[str]:
    """
    Split the search string into individual terms, stripping whitespace and quotes.

    Args:
        search_str: The user's search string.

    Returns:
        A list of search terms.
    """

    search_terms = []
    for s in search_str.split():
        search_term = s.strip().strip("'").strip('"').strip()
        if s:
            search_terms.append(search_term)

    return search_terms


def get_number_value(search_term: str) -> int | float | None:
    """
    Attempt to parse the search term into a number.

    Args:
        search_term: The search term to parse.

    Returns:
        The number value of the search term, or None if it cannot be parsed into a number.
    """

    try:
        return int(search_term)
    except Exception:
        pass

    try:
        return float(search_term)
    except Exception:
        pass

    return None


def get_date_value(search_term: str) -> datetime | None:
    """
    Attempt to parse the search term into a date.

    Args:
        search_term: The search term to parse.

    Returns:
        The datetime value of the search term, or None if it cannot be parsed into a date.
    """

    try:
        return datetime.fromisoformat(search_term)
    except Exception:
        pass

    for fmt in ["%Y-%m-%d", "%Y-%m", "%Y"]:
        try:
            return datetime.strptime(search_term, fmt)
        except Exception:
            pass

    return None


def get_year_value(search_term: str) -> int | None:
    """
    Attempt to parse the search term into a year.

    Args:
        search_term: The search term to parse.

    Returns:
        The year value of the search term, or None if it cannot be parsed into a year.
    """

    try:
        return datetime.strptime(search_term, "%Y").year
    except Exception:
        return None


def get_bool_value(search_term: str) -> bool | None:
    """
    Attempt to parse the search term into a boolean.

    Args:
        search_term: The search term to parse.

    Returns:
        The boolean value of the search term, or None if it cannot be parsed into a boolean.
    """

    if search_term.lower().strip() in ["true", "false"]:
        return search_term.lower() == "true"
    else:
        return None


def build_search(search_str: str, onyx_fields: dict[str, OnyxField]) -> Q:
    """
    Build a Q object that checks the user's search against the provided fields.

    Args:
        search_str: The user's search string.
        onyx_fields: A dictionary of field names to OnyxField objects that can be searched against.

    Returns:
        A Q object representing the search.
    """

    # Fields to search over
    text_fields = [
        field
        for field, onyx_field in onyx_fields.items()
        if onyx_field.onyx_type == OnyxType.TEXT
        or onyx_field.onyx_type == OnyxType.CHOICE
    ]
    number_fields = [
        field
        for field, onyx_field in onyx_fields.items()
        if onyx_field.onyx_type == OnyxType.INTEGER
        or onyx_field.onyx_type == OnyxType.DECIMAL
    ]
    date_fields = [
        field
        for field, onyx_field in onyx_fields.items()
        if onyx_field.onyx_type == OnyxType.DATE
        or onyx_field.onyx_type == OnyxType.DATETIME
    ]
    boolean_fields = [
        field
        for field, onyx_field in onyx_fields.items()
        if onyx_field.onyx_type == OnyxType.BOOLEAN
    ]

    # Split the search string into individual terms
    search_terms = get_search_terms(search_str)

    # Form the Q object for the search
    query = Q()
    matched_field = False

    for search_term in search_terms:
        q = Q()

        for field in text_fields:
            matched_field = True

            if field == "site":
                q |= Q(**{f"{field}__code__icontains": search_term})
            else:
                q |= Q(**{f"{field}__icontains": search_term})

        # If the search term can be parsed into a number, search over number fields
        number_value = get_number_value(search_term)

        if number_value is not None:
            matched_field = True

            for field in number_fields:
                q |= Q(**{field: number_value})

        # If the search term can be parsed into a date, search over date fields
        date_value = get_date_value(search_term)

        if date_value is not None:
            matched_field = True

            for field in date_fields:
                q |= Q(**{field: date_value})

        # If the search term can be parsed into a year, search over date fields for that year
        year_value = get_year_value(search_term)

        if year_value is not None:
            matched_field = True

            for field in date_fields:
                q |= Q(**{f"{field}__year": year_value})

        # If the search term can be parsed into bool, search over boolean fields
        bool_value = get_bool_value(search_term)

        if bool_value is not None:
            matched_field = True

            for field in boolean_fields:
                q |= Q(**{field: bool_value})

        query &= q

    # If there were no valid search fields, return a Q object that effectively evaluates to False
    if not matched_field:
        query = Q(pk__in=[])

    # Return the search object
    return query
