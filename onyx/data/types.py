from enum import Enum


class Actions(Enum):
    ACCESS = ("access", "access")
    NO_ACCESS = ("noaccess", "not access")
    GET = ("get", "get")
    LIST = ("list", "list")
    FILTER = ("filter", "filter")
    HISTORY = ("history", "get the history of")
    IDENTIFY = ("identify", "identify values from")
    ADD = ("add", "create")
    TEST_ADD = ("testadd", "test creating")
    CHANGE = ("change", "update")
    TEST_CHANGE = ("testchange", "test updating")
    DELETE = ("delete", "delete")

    def __init__(self, label: str, description: str) -> None:
        self.label = label
        self.description = description


class Scopes(Enum):
    ADMIN = "admin"
    UPLOADER = "uploader"
    ANALYST = "analyst"
    ANALYSIS_UPLOADER = "analysis_uploader"

    def __init__(self, label: str) -> None:
        self.label = label


class Objects(Enum):
    OBJECT = "object"
    RECORD = "records"
    ANALYSIS = "analyses"

    def __init__(self, label: str) -> None:
        self.label = label


class OnyxLookup(Enum):
    EXACT = (
        "exact",
        "The field's value must be equal to the query value.",
    )
    NE = (
        "ne",
        "The field's value must not be equal to the query value.",
    )
    IN = (
        "in",
        "The field's value must be in the list of query values.",
    )
    NOTIN = (
        "notin",
        "The field's value must not be in the list of query values.",
    )
    CONTAINS = (
        "contains",
        "The field's value must contain the query value.",
    )
    STARTSWITH = (
        "startswith",
        "The field's value must start with the query value.",
    )
    ENDSWITH = (
        "endswith",
        "The field's value must end with the query value.",
    )
    IEXACT = (
        "iexact",
        "The field's value must be equal to the query value, ignoring case.",
    )
    ICONTAINS = (
        "icontains",
        "The field's value must contain the query value, ignoring case.",
    )
    ISTARTSWITH = (
        "istartswith",
        "The field's value must start with the query value, ignoring case.",
    )
    IENDSWITH = (
        "iendswith",
        "The field's value must end with the query value, ignoring case.",
    )
    LENGTH = (
        "length",
        "The length of the field's value must be equal to the query value.",
    )
    LENGTH_IN = (
        "length__in",
        "The length of the field's value must be in the list of query values.",
    )
    LENGTH_RANGE = (
        "length__range",
        "The length of the field's value must be in the range of query values.",
    )
    LT = (
        "lt",
        "The field's value must be less than the query value.",
    )
    LTE = (
        "lte",
        "The field's value must be less than or equal to the query value.",
    )
    GT = (
        "gt",
        "The field's value must be greater than the query value.",
    )
    GTE = (
        "gte",
        "The field's value must be greater than or equal to the query value.",
    )
    RANGE = (
        "range",
        "The field's value must be in the range of query values.",
    )
    ISO_YEAR = (
        "iso_year",
        "The ISO 8601 week-numbering year of the field's value must be equal to the query value.",
    )
    ISO_YEAR_IN = (
        "iso_year__in",
        "The ISO 8601 week-numbering year of the field's value must be in the list of query values.",
    )
    ISO_YEAR_RANGE = (
        "iso_year__range",
        "The ISO 8601 week-numbering year of the field's value must be in the range of query values.",
    )
    WEEK = (
        "week",
        "The ISO 8601 week number of the field's value must be equal to the query value.",
    )
    WEEK_IN = (
        "week__in",
        "The ISO 8601 week number of the field's value must be in the list of query values.",
    )
    WEEK_RANGE = (
        "week__range",
        "The ISO 8601 week number of the field's value must be in the range of query values.",
    )
    ISNULL = (
        "isnull",
        "The field's value must be empty.",
    )
    CONTAINED_BY = (
        "contained_by",
        "The field's value must be equal to, or a subset of, the query value.",
    )
    OVERLAP = (
        "overlap",
        "The field's value must overlap with the query value.",
    )
    HAS_KEY = (
        "has_key",
        "The field's top-level keys must contain the query value.",
    )
    HAS_KEYS = (
        "has_keys",
        "The field's top-level keys must contain all of the query values.",
    )
    HAS_ANY_KEYS = (
        "has_any_keys",
        "The field's top-level keys must contain any of the query values.",
    )

    def __init__(self, label, description) -> None:
        self.label = label
        self.description = description

    @classmethod
    def lookups(cls):
        """
        Returns the set of all lookup labels.
        """

        return {""} | {lookup.label for lookup in cls}


TEXT_LOOKUPS = [
    "",
    OnyxLookup.EXACT.label,
    OnyxLookup.NE.label,
    OnyxLookup.IN.label,
    OnyxLookup.NOTIN.label,
    OnyxLookup.CONTAINS.label,
    OnyxLookup.STARTSWITH.label,
    OnyxLookup.ENDSWITH.label,
    OnyxLookup.IEXACT.label,
    OnyxLookup.ICONTAINS.label,
    OnyxLookup.ISTARTSWITH.label,
    OnyxLookup.IENDSWITH.label,
    OnyxLookup.LENGTH.label,
    OnyxLookup.LENGTH_IN.label,
    OnyxLookup.LENGTH_RANGE.label,
    OnyxLookup.ISNULL.label,
]

NUMBER_LOOKUPS = [
    "",
    OnyxLookup.EXACT.label,
    OnyxLookup.NE.label,
    OnyxLookup.IN.label,
    OnyxLookup.NOTIN.label,
    OnyxLookup.LT.label,
    OnyxLookup.LTE.label,
    OnyxLookup.GT.label,
    OnyxLookup.GTE.label,
    OnyxLookup.RANGE.label,
    OnyxLookup.ISNULL.label,
]

DATE_LOOKUPS = [
    "",
    OnyxLookup.EXACT.label,
    OnyxLookup.NE.label,
    OnyxLookup.IN.label,
    OnyxLookup.NOTIN.label,
    OnyxLookup.LT.label,
    OnyxLookup.LTE.label,
    OnyxLookup.GT.label,
    OnyxLookup.GTE.label,
    OnyxLookup.RANGE.label,
    OnyxLookup.ISO_YEAR.label,
    OnyxLookup.ISO_YEAR_IN.label,
    OnyxLookup.ISO_YEAR_RANGE.label,
    OnyxLookup.WEEK.label,
    OnyxLookup.WEEK_IN.label,
    OnyxLookup.WEEK_RANGE.label,
    OnyxLookup.ISNULL.label,
]


class OnyxType(Enum):
    ID = (
        "id",
        "A unique identifier for an object.",
        TEXT_LOOKUPS,
    )
    TEXT = (
        "text",
        "A string of characters.",
        TEXT_LOOKUPS,
    )
    CHOICE = (
        "choice",
        "A restricted set of options.",
        [
            "",
            OnyxLookup.EXACT.label,
            OnyxLookup.NE.label,
            OnyxLookup.IN.label,
            OnyxLookup.NOTIN.label,
            OnyxLookup.ISNULL.label,
        ],
    )
    INTEGER = (
        "integer",
        "A whole number.",
        NUMBER_LOOKUPS,
    )
    DECIMAL = (
        "decimal",
        "A decimal number.",
        NUMBER_LOOKUPS,
    )
    DATE = (
        "date",
        "A date.",
        DATE_LOOKUPS,
    )
    DATETIME = (
        "datetime",
        "A date and time.",
        DATE_LOOKUPS,
    )
    BOOLEAN = (
        "bool",
        "A true or false value.",
        [
            "",
            OnyxLookup.EXACT.label,
            OnyxLookup.NE.label,
            OnyxLookup.IN.label,
            OnyxLookup.NOTIN.label,
            OnyxLookup.ISNULL.label,
        ],
    )
    RELATION = (
        "relation",
        "A link to a row, or multiple rows, in another table.",
        [
            OnyxLookup.ISNULL.label,
        ],
    )
    ARRAY = (
        "array",
        "A list of values.",
        [
            "",
            OnyxLookup.EXACT.label,
            OnyxLookup.CONTAINS.label,
            OnyxLookup.CONTAINED_BY.label,
            OnyxLookup.OVERLAP.label,
            OnyxLookup.LENGTH.label,
            OnyxLookup.LENGTH_IN.label,
            OnyxLookup.LENGTH_RANGE.label,
            OnyxLookup.ISNULL.label,
        ],
    )
    STRUCTURE = (
        "structure",
        "An arbitrary JSON structure.",
        [
            "",
            OnyxLookup.EXACT.label,
            OnyxLookup.CONTAINS.label,
            OnyxLookup.CONTAINED_BY.label,
            OnyxLookup.HAS_KEY.label,
            OnyxLookup.HAS_KEYS.label,
            OnyxLookup.HAS_ANY_KEYS.label,
            OnyxLookup.ISNULL.label,
        ],
    )
    IDENTIFIERS = (
        "identifiers",
        "A many-to-many linkage with another table, captured in a set of identifiers.",
        [
            OnyxLookup.ISNULL.label,
        ],
    )

    def __init__(self, label, description, lookups) -> None:
        self.label = label
        self.description = description
        self.lookups = lookups
