# Lookups

*Lookups* can be used to specify more complex conditions that fields must match when filtering.

Different [types][types] have different lookups available to them. 

## `exact`

[`[text]`][text]
[`[choice]`][choice]
[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]
[`[bool]`][bool]
[`[array]`][array]
[`[structure]`][structure]

Return values equal to the search value.

## `ne`
[`[text]`][text]
[`[choice]`][choice]
[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]
[`[bool]`][bool]

Return values not equal to the search value.

## `in`

[`[text]`][text]
[`[choice]`][choice]
[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]
[`[bool]`][bool]

Return values that are within the set of search values.

## `notin`

[`[text]`][text]
[`[choice]`][choice]
[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]
[`[bool]`][bool]

Return values that are not within the set of search values.

## `contains`

[`[text]`][text]
[`[array]`][array]
[`[structure]`][structure]

Return values that contain the search value.

## `startswith`

[`[text]`][text]

Return values that start with the search value.

## `endswith`

[`[text]`][text]

Return values that end with the search value.

## `iexact`

[`[text]`][text]

Return values case-insensitively equal to the search value.

## `icontains`

[`[text]`][text]

Return values that case-insensitively contain the search value.

## `istartswith`

[`[text]`][text]

Return values that case-insensitively start with the search value.

## `iendswith`

[`[text]`][text]

Return values that case-insensitively end with the search value.

## `length`

[`[text]`][text]
[`[array]`][array]

Return values with a length equal to the search value.

## `length__in`

[`[text]`][text]
[`[array]`][array]

Return values with a length that is within the set of search values.

## `length__range`

[`[text]`][text]
[`[array]`][array]

Return values with a length that is within an inclusive range of search values.

## `lt`

[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]

Return values less than the search value.

## `lte`

[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]

Return values less than or equal to the search value.

## `gt`

[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]

Return values greater than the search value.

## `gte`

[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]

Return values greater than or equal to the search value.

## `range`

[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]

Return values within an inclusive range of search values.

## `iso_year`

[`[date]`][date]
[`[datetime]`][datetime]

Return values with an ISO 8601 week-numbering year equal to the search year.

## `iso_year__in`

[`[date]`][date]
[`[datetime]`][datetime]

Return values with an ISO 8601 week-numbering year that is within the set of search years.

## `iso_year__range`

[`[date]`][date]
[`[datetime]`][datetime]

Return values with an ISO 8601 week-numbering year that is within an inclusive range of search years.

## `week`

[`[date]`][date]
[`[datetime]`][datetime]

Return values with an ISO 8601 week number equal to the search number.

## `week__in`

[`[date]`][date]
[`[datetime]`][datetime]

Return values with an ISO 8601 week number that is within the set of search numbers.

## `week__range`

[`[date]`][date]
[`[datetime]`][datetime]

Return values with an ISO 8601 week number that is within an inclusive range of search numbers.

## `isnull`

[`[text]`][text]
[`[choice]`][choice]
[`[integer]`][integer]
[`[decimal]`][decimal]
[`[date]`][date]
[`[datetime]`][datetime]
[`[bool]`][bool]
[`[relation]`][relation]
[`[array]`][array]
[`[structure]`][structure]

Return values that are empty (`isnull = True`) or non-empty (`isnull = False`). 

* For [`text`][text] and [`choice`][choice] types, 'empty' is defined as the empty string `""`. 
* For the [`relation`][relation] type, 'empty' is defined as there being zero items linked to the record being evaluated.
* For the [`array`][array] type, 'empty' is defined as the empty array `[]`.
* For the [`structure`][structure] type, 'empty' is defined as the empty structure `{}`.
* For all other types, 'empty' is the SQL `null` value.

## `contained_by`

[`[array]`][array]
[`[structure]`][structure]

Return values that are equal to, or a subset of, the search value.

## `overlap`

[`[array]`][array]

Return values that overlap with the search value.

## `has_key`

[`[structure]`][structure]

Return values that have a top-level key which contains the search value.

## `has_keys`

[`[structure]`][structure]

Return values that have top-level keys which contains all of the search values.

## `has_any_keys`

[`[structure]`][structure]

Return values that have top-level keys which contains any of the search values.