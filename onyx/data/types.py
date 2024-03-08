from enum import Enum


class OnyxType(Enum):
    TEXT = (
        "text",
        [
            "",
            "exact",
            "ne",
            "in",
            "contains",
            "startswith",
            "endswith",
            "iexact",
            "icontains",
            "istartswith",
            "iendswith",
            "regex",
            "iregex",
            "length",
            "length__in",
            "length__range",
            "isnull",
        ],
    )
    CHOICE = (
        "choice",
        [
            "",
            "exact",
            "ne",
            "in",
            "isnull",
        ],
    )
    INTEGER = (
        "integer",
        [
            "",
            "exact",
            "ne",
            "in",
            "lt",
            "lte",
            "gt",
            "gte",
            "range",
            "isnull",
        ],
    )
    DECIMAL = (
        "decimal",
        [
            "",
            "exact",
            "ne",
            "in",
            "lt",
            "lte",
            "gt",
            "gte",
            "range",
            "isnull",
        ],
    )
    DATE_YYYY_MM = (
        "date (YYYY-MM)",
        [
            "",
            "exact",
            "ne",
            "in",
            "lt",
            "lte",
            "gt",
            "gte",
            "range",
            # "year",
            # "year__in",
            # "year__range",
            "isnull",
        ],
    )
    DATE_YYYY_MM_DD = (
        "date (YYYY-MM-DD)",
        [
            "",
            "exact",
            "ne",
            "in",
            "lt",
            "lte",
            "gt",
            "gte",
            "range",
            # "year",
            # "year__in",
            # "year__range",
            "iso_year",
            "iso_year__in",
            "iso_year__range",
            "week",
            "week__in",
            "week__range",
            "isnull",
        ],
    )
    DATETIME = (
        "date (YYYY-MM-DD HH:MM:SS)",
        [
            "",
            "exact",
            "ne",
            "in",
            "lt",
            "lte",
            "gt",
            "gte",
            "range",
            # "year",
            # "year__in",
            # "year__range",
            "iso_year",
            "iso_year__in",
            "iso_year__range",
            "week",
            "week__in",
            "week__range",
            "isnull",
        ],
    )
    BOOLEAN = (
        "bool",
        [
            "",
            "exact",
            "ne",
            "in",
            "isnull",
        ],
    )
    RELATION = (
        "relation",
        [
            "isnull",
        ],
    )

    def __init__(self, label, lookups) -> None:
        self.label = label
        self.lookups = lookups


ALL_LOOKUPS = set(lookup for onyx_type in OnyxType for lookup in onyx_type.lookups)
