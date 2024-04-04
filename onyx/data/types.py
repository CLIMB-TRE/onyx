from enum import Enum


class OnyxType(Enum):
    TEXT = (
        "text",
        [
            "",
            "exact",
            "ne",
            "in",
            "notin",
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
            "notin",
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
            "notin",
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
            "notin",
            "lt",
            "lte",
            "gt",
            "gte",
            "range",
            "isnull",
        ],
    )
    DATE = (
        "date",
        [
            "",
            "exact",
            "ne",
            "in",
            "notin",
            "lt",
            "lte",
            "gt",
            "gte",
            "range",
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
        "datetime",
        [
            "",
            "exact",
            "ne",
            "in",
            "notin",
            "lt",
            "lte",
            "gt",
            "gte",
            "range",
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
            "notin",
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
