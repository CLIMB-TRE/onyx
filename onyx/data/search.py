import operator
import functools
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
        if search_term:
            search_terms.append(search_term)

    return search_terms


def get_integer_value(search_term: str) -> int | None:
    """
    Attempt to parse the search term into an integer.

    Args:
        search_term: The search term to parse.

    Returns:
        The integer value of the search term, or None if it cannot be parsed into an integer.
    """

    try:
        return int(search_term)
    except Exception:
        pass

    try:
        float_value = float(search_term)
        if float_value.is_integer():
            return int(float_value)
    except Exception:
        pass

    return None


def get_decimal_value(search_term: str) -> float | None:
    """
    Attempt to parse the search term into a decimal.

    Args:
        search_term: The search term to parse.

    Returns:
        The decimal value of the search term, or None if it cannot be parsed into a decimal.
    """

    try:
        return float(search_term)
    except Exception:
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

    if search_term.lower() in ["true", "false"]:
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
    integer_fields = [
        field
        for field, onyx_field in onyx_fields.items()
        if onyx_field.onyx_type == OnyxType.INTEGER
    ]
    decimal_fields = [
        field
        for field, onyx_field in onyx_fields.items()
        if onyx_field.onyx_type == OnyxType.DECIMAL
    ]
    date_fields = [
        field
        for field, onyx_field in onyx_fields.items()
        if onyx_field.onyx_type == OnyxType.DATE
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

    for search_term in search_terms:
        qs = []

        # Search over text fields using case-insensitive containment
        for field in text_fields:
            if field == "site":
                qs.append(Q(**{f"{field}__code__icontains": search_term}))
            else:
                qs.append(Q(**{f"{field}__icontains": search_term}))

        # Search over integer fields if the search term can be parsed into an integer
        int_value = get_integer_value(search_term)
        if int_value is not None:
            for field in integer_fields:
                qs.append(Q(**{field: int_value}))

        # Search over decimal fields if the search term can be parsed into a decimal
        decimal_value = get_decimal_value(search_term)
        if decimal_value is not None:
            for field in decimal_fields:
                qs.append(Q(**{field: decimal_value}))

        # Search over date fields if the search term can be parsed into a date
        date_value = get_date_value(search_term)
        if date_value is not None:
            for field in date_fields:
                qs.append(Q(**{field: date_value}))

        # Search over date fields for year if the search term can be parsed into a year
        year_value = get_year_value(search_term)
        if year_value is not None:
            for field in date_fields:
                qs.append(Q(**{f"{field}__year": year_value}))

        # Search over boolean fields if the search term can be parsed into a boolean
        bool_value = get_bool_value(search_term)
        if bool_value is not None:
            for field in boolean_fields:
                qs.append(Q(**{field: bool_value}))

        # Add the Q objects for this term to the overall search query
        # These are OR-ed together to allow the term to match any of the fields
        # And then AND-ed with the overall query to combine with other search terms
        # If there are no Q objects for this term, add a Q object representing no match
        if qs:
            query &= functools.reduce(operator.or_, qs)
        else:
            query &= Q(pk__in=[])

    # Return the search object
    return query
