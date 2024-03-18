# Data types

## Text
**OnyxType**: `OnyxType.TEXT` 

**Label**: `text`

**Lookups**:
```
{
    "": "<class 'django_filters.filters.CharFilter'>",
    "exact": "<class 'django_filters.filters.CharFilter'>",
    "ne": "<class 'django_filters.filters.CharFilter'>",
    "in": "<class 'data.filters.CharInFilter'>",
    "contains": "<class 'django_filters.filters.CharFilter'>",
    "startswith": "<class 'django_filters.filters.CharFilter'>",
    "endswith": "<class 'django_filters.filters.CharFilter'>",
    "iexact": "<class 'django_filters.filters.CharFilter'>",
    "icontains": "<class 'django_filters.filters.CharFilter'>",
    "istartswith": "<class 'django_filters.filters.CharFilter'>",
    "iendswith": "<class 'django_filters.filters.CharFilter'>",
    "regex": "<class 'data.filters.RegexFilter'>",
    "iregex": "<class 'data.filters.RegexFilter'>",
    "length": "<class 'django_filters.filters.NumberFilter'>",
    "length__in": "<class 'data.filters.NumberInFilter'>",
    "length__range": "<class 'data.filters.NumberRangeFilter'>",
    "isnull": "<class 'data.filters.BooleanFilter'>"
}
```

## Choice
**OnyxType**: `OnyxType.CHOICE`

**Label**: `choice`

**Lookups**:
```
{
    "": "<class 'data.filters.ChoiceFilter'>",
    "exact": "<class 'data.filters.ChoiceFilter'>",
    "ne": "<class 'data.filters.ChoiceFilter'>",
    "in": "<class 'data.filters.ChoiceInFilter'>",
    "isnull": "<class 'data.filters.BooleanFilter'>"
}
```

## Integer
**OnyxType**: `OnyxType.INTEGER`

**Label**: `integer`

**Lookups**:
```
{
    "": "<class 'django_filters.filters.NumberFilter'>",
    "exact": "<class 'django_filters.filters.NumberFilter'>",
    "ne": "<class 'django_filters.filters.NumberFilter'>",
    "in": "<class 'data.filters.NumberInFilter'>",
    "lt": "<class 'django_filters.filters.NumberFilter'>",
    "lte": "<class 'django_filters.filters.NumberFilter'>",
    "gt": "<class 'django_filters.filters.NumberFilter'>",
    "gte": "<class 'django_filters.filters.NumberFilter'>",
    "range": "<class 'data.filters.NumberRangeFilter'>",
    "isnull": "<class 'data.filters.BooleanFilter'>"
}
```

## Decimal
**OnyxType**: `OnyxType.DECIMAL`

**Label**: `decimal`

**Lookups**:
```
{
    "": "<class 'django_filters.filters.NumberFilter'>",
    "exact": "<class 'django_filters.filters.NumberFilter'>",
    "ne": "<class 'django_filters.filters.NumberFilter'>",
    "in": "<class 'data.filters.NumberInFilter'>",
    "lt": "<class 'django_filters.filters.NumberFilter'>",
    "lte": "<class 'django_filters.filters.NumberFilter'>",
    "gt": "<class 'django_filters.filters.NumberFilter'>",
    "gte": "<class 'django_filters.filters.NumberFilter'>",
    "range": "<class 'data.filters.NumberRangeFilter'>",
    "isnull": "<class 'data.filters.BooleanFilter'>"
}
```

## Date
**OnyxType**: `OnyxType.DATE`

**Label**: `date`

**Lookups**:
```
 {
    "": "<class 'data.filters.DateFilter'>",
    "exact": "<class 'data.filters.DateFilter'>",
    "ne": "<class 'data.filters.DateFilter'>",
    "in": "<class 'data.filters.DateInFilter'>",
    "lt": "<class 'data.filters.DateFilter'>",
    "lte": "<class 'data.filters.DateFilter'>",
    "gt": "<class 'data.filters.DateFilter'>",
    "gte": "<class 'data.filters.DateFilter'>",
    "range": "<class 'data.filters.DateRangeFilter'>",
    "iso_year": "<class 'django_filters.filters.NumberFilter'>",
    "iso_year__in": "<class 'data.filters.NumberInFilter'>",
    "iso_year__range": "<class 'data.filters.NumberRangeFilter'>",
    "week": "<class 'django_filters.filters.NumberFilter'>",
    "week__in": "<class 'data.filters.NumberInFilter'>",
    "week__range": "<class 'data.filters.NumberRangeFilter'>",
    "isnull": "<class 'data.filters.BooleanFilter'>"
}
```

## Datetime
**OnyxType**: `OnyxType.DATETIME`

**Label**: `date`

**Lookups**:
```
{
    "": "<class 'data.filters.DateTimeFilter'>",
    "exact": "<class 'data.filters.DateTimeFilter'>",
    "ne": "<class 'data.filters.DateTimeFilter'>",
    "in": "<class 'data.filters.DateTimeInFilter'>",
    "lt": "<class 'data.filters.DateTimeFilter'>",
    "lte": "<class 'data.filters.DateTimeFilter'>",
    "gt": "<class 'data.filters.DateTimeFilter'>",
    "gte": "<class 'data.filters.DateTimeFilter'>",
    "range": "<class 'data.filters.DateTimeRangeFilter'>",
    "iso_year": "<class 'django_filters.filters.NumberFilter'>",
    "iso_year__in": "<class 'data.filters.NumberInFilter'>",
    "iso_year__range": "<class 'data.filters.NumberRangeFilter'>",
    "week": "<class 'django_filters.filters.NumberFilter'>",
    "week__in": "<class 'data.filters.NumberInFilter'>",
    "week__range": "<class 'data.filters.NumberRangeFilter'>",
    "isnull": "<class 'data.filters.BooleanFilter'>"
}
```

## Boolean
**OnyxType**: `OnyxType.BOOLEAN`

**Label**: `bool`

**Lookups**:
```
{
    "": "<class 'data.filters.BooleanFilter'>",
    "exact": "<class 'data.filters.BooleanFilter'>",
    "ne": "<class 'data.filters.BooleanFilter'>",
    "in": "<class 'data.filters.BooleanInFilter'>",
    "isnull": "<class 'data.filters.BooleanFilter'>"
}
```

## Relation
**OnyxType**: `OnyxType.RELATION`

**Label**: `relation`

**Lookups**:
```
{
    "isnull": "<class 'data.filters.BooleanFilter'>"
}
```